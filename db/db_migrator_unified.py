from __future__ import annotations

import hashlib
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import pandas as pd

from db.db_config import (
    CSV_OUTPUT_DIR,
    KEY_JOINER,
    ListingConfig,
    PRIMARY_KEY_COLUMN,
    SCHEMA_FILE,
    SCHEMA_SHEET,
    SQLITE_DB,
)

SQL_TYPE_MAP = {
    'INTEGER': 'INTEGER',
    'DECIMAL': 'REAL',
    'NUMERIC': 'REAL',
    'STRING': 'TEXT',
    'LIST/BLOB': 'TEXT',
}


def normalize_column_names(columns: Iterable[Any]) -> List[str]:
    seen: Dict[str, int] = {}
    normalized: List[str] = []
    for raw in columns:
        base = str(raw).strip().upper().replace(".", "__")
        count = seen.get(base, 0)
        if count == 0:
            normalized.append(base)
        else:
            normalized.append(f"{base}_{count}")
        seen[base] = count + 1
    return normalized


def uppercase_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Convert string columns to uppercase while preserving numeric types."""
    result = df.copy()
    for col in result.columns:
        # Only uppercase string/object columns; preserve numeric types
        if result[col].dtype == 'object':
            result[col] = result[col].map(lambda v: "" if pd.isna(v) else str(v).upper())
    return result


def load_schema(
    path: Path | str = SCHEMA_FILE,
    sheet: str = SCHEMA_SHEET,
    extra_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    schema_path = Path(path)
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    schema = pd.read_excel(schema_path, sheet_name=sheet)
    required_mask = schema["needed?"].astype(str).str.upper().eq("Y")
    required = schema[required_mask]
    normalized = normalize_column_names(required["name"].tolist())
    # Include dtype information from the schema
    schema_df = pd.DataFrame({
        "name": normalized,
        "dtype": required["dtype"].fillna("STRING").tolist()
    })
    if extra_columns:
        extra_normalized = normalize_column_names(extra_columns)
        extras_df = pd.DataFrame({
            "name": extra_normalized,
            "dtype": ["STRING"] * len(extra_normalized)
        })
        schema_df = (
            pd.concat([schema_df, extras_df], ignore_index=True)
            .drop_duplicates(subset="name", keep="first")
            .reset_index(drop=True)
        )
    return schema_df


def align_to_schema(df: pd.DataFrame, schema: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame.columns = normalize_column_names(frame.columns)
    desired_columns = schema["name"].tolist()
    return frame.reindex(columns=desired_columns, fill_value="")


def persist_to_csv(df: pd.DataFrame, csv_prefix: str) -> str:
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{csv_prefix}{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    file_path = CSV_OUTPUT_DIR / filename
    df.to_csv(file_path, index=False)
    return str(file_path)


def build_sql_schema(schema: pd.DataFrame) -> str:
    """Build SQL schema respecting dtype specifications from Excel schema."""
    # Map Excel dtype specifications to SQLite types
    col_defs = []
    for idx, row in schema.iterrows():
        col = row['name']
        # Get dtype from schema, default to TEXT
        excel_dtype = str(row.get('dtype', 'STRING')).upper()
        sql_type = _sql_type_from_excel(excel_dtype)

        if col == PRIMARY_KEY_COLUMN:
            col_defs.append(f"{col} TEXT PRIMARY KEY")
        else:
            col_defs.append(f"{col} {sql_type}")
    return ", ".join(col_defs)


def _sql_type_from_excel(value: str) -> str:
    key = (value or "STRING").strip().upper()
    return SQL_TYPE_MAP.get(key, "TEXT")


def _sql_type_matches(actual: str, expected: str) -> bool:
    actual_norm = (actual or "").upper()
    expected_norm = (expected or "TEXT").upper()

    if expected_norm == "INTEGER":
        return "INT" in actual_norm
    if expected_norm == "REAL":
        return any(token in actual_norm for token in ("REAL", "NUMERIC", "DECIMAL", "DOUBLE", "FLOAT"))
    return any(token in actual_norm for token in ("TEXT", "CHAR", "CLOB"))


def _schema_needs_rebuild(info_rows: Sequence[tuple], schema: pd.DataFrame) -> bool:
    actual_columns = {row[1]: row[2] for row in info_rows}
    for _, row in schema.iterrows():
        col = row["name"]
        expected_type = _sql_type_from_excel(str(row.get("dtype", "STRING")))
        actual_type = actual_columns.get(col)
        if not actual_type:
            return True
        if not _sql_type_matches(actual_type, expected_type):
            return True
    return False


def _ensure_unique_index(conn: sqlite3.Connection, table_name: str, columns: Sequence[str]) -> None:
    if not columns:
        return
    existing_columns = {
        row[1] for row in conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    }
    applicable = [col for col in columns if col in existing_columns]
    if not applicable:
        return
    index_name = f"ux_{table_name}_{'_'.join(applicable).lower()}"
    existing_indexes = {
        row[1] for row in conn.execute(f"PRAGMA index_list('{table_name}')").fetchall()
    }
    if index_name not in existing_indexes:
        columns_sql = ", ".join(applicable)
        conn.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns_sql});"
        )
        conn.commit()


def _ensure_primary_key_schema(
    conn: sqlite3.Connection, table_name: str, schema: pd.DataFrame, unique_key_columns: Sequence[str]
) -> None:
    info = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    if not info:
        return
    has_primary_key = any(column[1] == PRIMARY_KEY_COLUMN and column[5] == 1 for column in info)
    schema_mismatch = _schema_needs_rebuild(info, schema)
    if not has_primary_key or schema_mismatch:
        _rebuild_table_with_primary_key(conn, table_name, schema, unique_key_columns)


def _rebuild_table_with_primary_key(
    conn: sqlite3.Connection, table_name: str, schema: pd.DataFrame, unique_key_columns: Sequence[str]
) -> None:
    backup_table = f"{table_name}__legacy_pk"
    conn.execute(f"DROP TABLE IF EXISTS {backup_table}")
    conn.commit()
    conn.execute(f"ALTER TABLE {table_name} RENAME TO {backup_table}")
    conn.commit()

    schema_sql = build_sql_schema(schema)
    conn.execute(f"CREATE TABLE {table_name} ({schema_sql});")
    conn.commit()

    insert_columns = schema["name"].tolist()
    placeholders = ", ".join("?" for _ in insert_columns)
    insert_sql = f"INSERT INTO {table_name} ({', '.join(insert_columns)}) VALUES ({placeholders})"
    cursor = conn.execute(f"SELECT rowid, * FROM {backup_table}")
    legacy_columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()

    for row in rows:
        row_data = {legacy_columns[idx]: row[idx] for idx in range(len(legacy_columns))}
        pk_seed_parts = []
        for column in unique_key_columns:
            pk_seed_parts.append(str(row_data.get(column, "") or "").strip().upper())
        pk_seed = KEY_JOINER.join(pk_seed_parts)
        pk_value = _hash_with_fallback(pk_seed, str(row_data.get("rowid", "")))

        values: List[Any] = []
        for column in insert_columns:
            if column == PRIMARY_KEY_COLUMN:
                values.append(pk_value)
            else:
                values.append(row_data.get(column, ""))
        conn.execute(insert_sql, values)

    conn.commit()
    conn.execute(f"DROP TABLE {backup_table}")
    conn.commit()


def ensure_table_exists(
    db_path: Path | str,
    table_name: str,
    schema: pd.DataFrame,
    unique_key_columns: Sequence[str]
) -> None:
    schema_sql = build_sql_schema(schema)
    create_statement = f"CREATE TABLE IF NOT EXISTS {table_name} ({schema_sql});"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(create_statement)
        conn.commit()
        _ensure_primary_key_schema(conn, table_name, schema, unique_key_columns)
        _ensure_unique_index(conn, table_name, unique_key_columns)


def _build_key_series(frame: pd.DataFrame, columns: Sequence[str]) -> pd.Series:
    if frame.empty or not columns:
        return pd.Series(dtype=str)
    safe = frame.loc[:, columns].fillna("").astype(str)
    return safe.apply(lambda row: KEY_JOINER.join(row.tolist()), axis=1)


def _build_primary_key_seed(frame: pd.DataFrame, columns: Sequence[str]) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=str, index=frame.index)
    if not columns:
        return pd.Series([""] * len(frame), index=frame.index, dtype=str)
    normalized = (
        frame.loc[:, columns]
        .fillna("")
        .astype(str)
        .apply(lambda col: col.str.strip().str.upper())
    )
    return normalized.apply(lambda row: KEY_JOINER.join(row.tolist()), axis=1)


def _hash_with_fallback(seed: str, fallback: str | None = None) -> str:
    candidate = (seed or "").strip()
    if not candidate and fallback:
        candidate = str(fallback).strip()
    if not candidate:
        return ""
    digest = hashlib.sha256(candidate.upper().encode("utf-8")).hexdigest()
    return digest.upper()


def assign_primary_keys(df: pd.DataFrame, unique_key_columns: Sequence[str]) -> pd.DataFrame:
    """Ensure the PRIMARY_KEY_COLUMN is populated for each row."""
    if df.empty:
        return df
    frame = df.copy()
    if PRIMARY_KEY_COLUMN not in frame.columns:
        frame[PRIMARY_KEY_COLUMN] = ""
    key_columns = [col for col in unique_key_columns if col in frame.columns]
    if not key_columns:
        return frame

    seeds = _build_primary_key_seed(frame, key_columns)
    fallback_series = pd.Series(frame.index.astype(str), index=frame.index)
    primary_keys = seeds.combine(fallback_series, _hash_with_fallback)
    missing_mask = frame[PRIMARY_KEY_COLUMN].astype(str).str.strip() == ""
    frame.loc[missing_mask, PRIMARY_KEY_COLUMN] = primary_keys.loc[missing_mask]
    return frame


def persist_to_sqlite(
    df: pd.DataFrame,
    config: ListingConfig,
    db_path: Path | str = SQLITE_DB
) -> None:
    frame = df.copy()
    if frame.empty:
        return

    frame = assign_primary_keys(frame, config.unique_key_columns)
    key_columns = [col for col in config.unique_key_columns if col in frame.columns]
    ingestion_column = "INGESTION_DATE" if "INGESTION_DATE" in frame.columns else None
    frame = frame.fillna("")
    with sqlite3.connect(str(db_path)) as conn:
        table_columns = [
            row[1] for row in conn.execute(f"PRAGMA table_info('{config.table_name}')").fetchall()
        ]
        if key_columns:
            frame = frame.drop_duplicates(subset=key_columns, keep="first")
            existing_keys_df = pd.read_sql(
                f"SELECT {', '.join(key_columns)} FROM {config.table_name}", conn
            )
            updated_count = 0
            if not existing_keys_df.empty:
                existing_keys = set(_build_key_series(existing_keys_df, key_columns))
                frame["_compound_key"] = _build_key_series(frame, key_columns)
                existing_mask = frame["_compound_key"].isin(existing_keys)

                if ingestion_column and existing_mask.any():
                    update_rows = frame.loc[existing_mask, key_columns + [ingestion_column]].copy()
                    update_rows = update_rows.fillna("")
                    update_sql = (
                        f'UPDATE {config.table_name} SET "{ingestion_column}" = ? WHERE '
                        + " AND ".join(f'"{col}" = ?' for col in key_columns)
                    )
                    update_params = [
                        (
                            str(row[ingestion_column]),
                            *[str(row[key]) for key in key_columns],
                        )
                        for _, row in update_rows.iterrows()
                    ]
                    if update_params:
                        conn.executemany(update_sql, update_params)
                        conn.commit()
                        updated_count = len(update_params)
                else:
                    updated_count = 0

                frame = frame.loc[~existing_mask].copy()
                if "_compound_key" in frame.columns:
                    frame = frame.drop(columns="_compound_key")
                if updated_count and frame.empty:
                    logging.info(
                        f"Updated {updated_count} existing records with latest ingestion date; no new rows inserted."
                    )
                    return
            else:
                if "_compound_key" in frame.columns:
                    frame = frame.drop(columns="_compound_key")
        else:
            frame = frame.drop_duplicates(keep="first")

        if frame.empty:
            logging.info("No new records to insert; existing table left unchanged.")
            return

        if table_columns:
            for column in table_columns:
                if column not in frame.columns:
                    frame[column] = ""
            frame = frame.reindex(columns=table_columns)

        frame.to_sql(config.table_name, conn, if_exists="append", index=False)
        conn.commit()
