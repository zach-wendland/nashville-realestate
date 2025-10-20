from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
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
    return df.applymap(lambda value: "" if pd.isna(value) else str(value).upper())


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
    filename = f"{CSV_PREFIX}{datetime.utcnow().strftime('%Y%m%d')}.csv"
    file_path = CSV_OUTPUT_DIR / filename
    df.to_csv(file_path, index=False)
    return str(file_path)


def build_sql_schema(schema: pd.DataFrame) -> str:
    col_defs = [f"{col} TEXT" for col in schema["name"]]
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


def ensure_table_exists(db_path: Path | str, table_name: str, schema: pd.DataFrame) -> None:
    schema_sql = build_sql_schema(schema)
    create_statement = f"CREATE TABLE IF NOT EXISTS {table_name} ({schema_sql});"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(create_statement)
        conn.commit()
        _ensure_unique_index(conn, table_name, UNIQUE_KEY_COLUMNS)


def _build_key_series(frame: pd.DataFrame, columns: Sequence[str]) -> pd.Series:
    if frame.empty or not columns:
        return pd.Series(dtype=str)
    safe = frame.loc[:, columns].fillna("").astype(str)
    return safe.apply(lambda row: KEY_JOINER.join(row.tolist()), axis=1)


def persist_to_sqlite(df: pd.DataFrame, db_path: Path | str = SQLITE_DB, table_name: str = TABLE_NAME) -> None:
    frame = df.copy()
    if frame.empty:
        return

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
