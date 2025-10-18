from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, Iterable, List

import pandas as pd

SCHEMA_FILE = "nashville-zillow-project.xlsx"
SCHEMA_SHEET = "zillow-rent-schema"
SQLITE_DB = "TESTRENT01.db"
TABLE_NAME = "NashvilleRents01"
CSV_PREFIX = "nsh-rent"


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


def load_schema(path: str = SCHEMA_FILE, sheet: str = SCHEMA_SHEET) -> pd.DataFrame:
    schema = pd.read_excel(path, sheet_name=sheet)
    required = schema[schema["needed?"].astype(str).str.upper().eq("Y")]["name"]
    normalized = normalize_column_names(required.tolist())
    return pd.DataFrame({"name": normalized})


def align_to_schema(df: pd.DataFrame, schema: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame.columns = normalize_column_names(frame.columns)
    desired_columns = schema["name"].tolist()
    return frame.reindex(columns=desired_columns, fill_value="")


def persist_to_csv(df: pd.DataFrame) -> str:
    filename = f"{CSV_PREFIX}{datetime.utcnow().strftime('%Y%m%d')}.csv"
    df.to_csv(filename, index=False)
    return filename


def build_sql_schema(schema: pd.DataFrame) -> str:
    col_defs = [f"{col} TEXT" for col in schema["name"]]
    return ", ".join(col_defs)


def ensure_table_exists(db_path: str, table_name: str, schema: pd.DataFrame) -> None:
    schema_sql = build_sql_schema(schema)
    create_statement = f"CREATE TABLE IF NOT EXISTS {table_name} ({schema_sql});"
    with sqlite3.connect(db_path) as conn:
        conn.execute(create_statement)
        conn.commit()


def persist_to_sqlite(df: pd.DataFrame, db_path: str = SQLITE_DB, table_name: str = TABLE_NAME) -> None:
    with sqlite3.connect(db_path) as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.commit()
