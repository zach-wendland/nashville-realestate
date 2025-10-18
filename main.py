from __future__ import annotations

from typing import Sequence

import pandas as pd

from db.db_migrator import (
    SQLITE_DB,
    TABLE_NAME,
    align_to_schema,
    ensure_table_exists,
    load_schema,
    normalize_column_names,
    persist_to_csv,
    persist_to_sqlite,
    uppercase_dataframe,
)
from api.zillow_fetcher import FetchConfig, fetch_dataframe, split_locations

BASE_PARAMS = {
    "status_type": "ForRent",
    "rentMinPrice": 1600,
    "rentMaxPrice": 3000,
    "bedsMin": 1,
    "bedsMax": 2,
    "sqftMin": 700,
}
RAW_LOCATIONS = "37206 Nashville, TN; 37216, Nashville, TN"
MAX_PAGES = 1
UNIT_FALLBACK_COLUMNS = {"PRICE": "PRICE_1", "BEDS": "BEDS_1", "BATHROOMS": "BATHROOMS_1"}


def _ensure_priority_columns(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    columns = normalize_column_names(frame.columns)
    frame.columns = columns
    for target, fallback in UNIT_FALLBACK_COLUMNS.items():
        if target not in frame.columns and fallback in frame.columns:
            frame[target] = frame[fallback]
    return frame


def build_pipeline_dataframe(locations: Sequence[str]) -> pd.DataFrame:
    config = FetchConfig(base_params=BASE_PARAMS, locations=locations, max_pages=MAX_PAGES)
    df_raw = fetch_dataframe(config)
    if df_raw.empty:
        return df_raw
    df_priority = _ensure_priority_columns(df_raw)
    return uppercase_dataframe(df_priority)


def main() -> None:
    locations = split_locations(RAW_LOCATIONS)
    frame = build_pipeline_dataframe(locations)

    if frame.empty:
        print("No records fetched; aborting persistence steps.")
        return

    schema = load_schema()
    aligned = align_to_schema(frame, schema)

    ensure_table_exists(SQLITE_DB, TABLE_NAME, schema)
    persist_to_sqlite(aligned, SQLITE_DB, TABLE_NAME)
    csv_path = persist_to_csv(aligned)

    print(f"SQLite table '{TABLE_NAME}' updated in {SQLITE_DB}.")
    print(f"CSV exported to {csv_path}")


if __name__ == "__main__":
    main()
