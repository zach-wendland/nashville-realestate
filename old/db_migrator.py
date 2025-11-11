from __future__ import annotations

import hashlib
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
EXCEL_DIR = BASE_DIR / "excel_files"
SCHEMA_FILE = EXCEL_DIR / "nashville-zillow-project.xlsx"
SCHEMA_SHEET = "zillow-rent-schema"
SQLITE_DB = BASE_DIR / "TESTRENT01.db"
TABLE_NAME = "NashvilleRents01"
CSV_PREFIX = "nsh-rent"
CSV_OUTPUT_DIR = EXCEL_DIR
UNIQUE_KEY_COLUMNS: Tuple[str, ...] = ("DETAILURL",)
KEY_JOINER = "__||__"
PRIMARY_KEY_COLUMN = "RECORD_ID"
PRIMARY_KEY_SOURCE_COLUMNS: Tuple[str, ...] = UNIQUE_KEY_COLUMNS


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
    return df.map(lambda value: "" if pd.isna(value) else str(value).upper())


def load_schema(
    path: Path | str = SCHEMA_FILE,
    sheet: str = SCHEMA_SHEET,
    extra_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    schema_path = Path(path)
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    schema = pd.read_excel(schema_path, sheet_name=sheet)
    required = schema[schema["needed?"].astype(str).str.upper().eq("Y")]["name"]
    normalized = normalize_column_names(required.tolist())
    schema_df = pd.DataFrame({"name": normalized})
    if extra_columns:
        extra_normalized = normalize_column_names(extra_columns)
        extras_df = pd.DataFrame({"name": extra_normalized})
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


def persist_to_csv(df: pd.DataFrame) -> str:
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{CSV_PREFIX}{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    file_path = CSV_OUTPUT_DIR / filename
    df.to_csv(file_path, index=False)
    return str(file_path)


def build_sql_schema(schema: pd.DataFrame) -> str:
    col_defs = []
    for col in schema["name"]:
        if col == PRIMARY_KEY_COLUMN:
            col_defs.append(f"{col} TEXT PRIMARY KEY")
        else:
            col_defs.append(f"{col} TEXT")
    return ", ".join(col_defs)


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
    conn: sqlite3.Connection, table_name: str, schema: pd.DataFrame
) -> None:
    info = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    if not info:
        return
    for column in info:
        name = column[1]
        is_primary = column[5] == 1
        if name == PRIMARY_KEY_COLUMN and is_primary:
            return
    _rebuild_table_with_primary_key(conn, table_name, schema)


def _rebuild_table_with_primary_key(
    conn: sqlite3.Connection, table_name: str, schema: pd.DataFrame
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
        for column in PRIMARY_KEY_SOURCE_COLUMNS:
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


def ensure_table_exists(db_path: Path | str, table_name: str, schema: pd.DataFrame) -> None:
    schema_sql = build_sql_schema(schema)
    create_statement = f"CREATE TABLE IF NOT EXISTS {table_name} ({schema_sql});"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(create_statement)
        conn.commit()
        _ensure_primary_key_schema(conn, table_name, schema)
        _ensure_unique_index(conn, table_name, UNIQUE_KEY_COLUMNS)


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


def assign_primary_keys(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the PRIMARY_KEY_COLUMN is populated for each row."""
    if df.empty:
        return df
    frame = df.copy()
    if PRIMARY_KEY_COLUMN not in frame.columns:
        frame[PRIMARY_KEY_COLUMN] = ""
    key_columns = [col for col in PRIMARY_KEY_SOURCE_COLUMNS if col in frame.columns]
    if not key_columns:
        return frame

    seeds = _build_primary_key_seed(frame, key_columns)
    fallback_series = pd.Series(frame.index.astype(str), index=frame.index)
    primary_keys = seeds.combine(fallback_series, _hash_with_fallback)
    missing_mask = frame[PRIMARY_KEY_COLUMN].astype(str).str.strip() == ""
    frame.loc[missing_mask, PRIMARY_KEY_COLUMN] = primary_keys.loc[missing_mask]
    return frame


def persist_to_sqlite(df: pd.DataFrame, db_path: Path | str = SQLITE_DB, table_name: str = TABLE_NAME) -> None:
    frame = df.copy()
    if frame.empty:
        return

    frame = assign_primary_keys(frame)
    key_columns = [col for col in UNIQUE_KEY_COLUMNS if col in frame.columns]
    ingestion_column = "INGESTION_DATE" if "INGESTION_DATE" in frame.columns else None
    frame = frame.fillna("")
    with sqlite3.connect(str(db_path)) as conn:
        table_columns = [
            row[1] for row in conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        ]
        if key_columns:
            frame = frame.drop_duplicates(subset=key_columns, keep="first")
            existing_keys_df = pd.read_sql(
                f"SELECT {', '.join(key_columns)} FROM {table_name}", conn
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
                        f'UPDATE {table_name} SET "{ingestion_column}" = ? WHERE '
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

        frame.to_sql(table_name, conn, if_exists="append", index=False)
        conn.commit()
