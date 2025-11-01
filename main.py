from __future__ import annotations

import logging
from typing import Sequence

import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
from utils.ingestionVars import ingestion_date

BASE_PARAMS = {
    "status_type": "ForRent",
    "rentMinPrice": 1600,
    "rentMaxPrice": 3000,
    "bedsMin": 1,
    "bedsMax": 4,
    "sqftMin": 700,
    "sqftMax": 3500,
}
# 20 Nashville zip codes covering diverse neighborhoods and rental markets
# Urban Core: 37201, 37203, 37212, 37219, 37208, 37209
# East Nashville: 37206, 37216, 37207
# South/Southeast: 37204, 37211, 37210, 37217
# North: 37218, 37214
# West/Southwest: 37205, 37215, 37213
# Suburban: 37027, 37221
RAW_LOCATIONS = "37206, Nashville, TN; 37216, Nashville, TN; 37207, Nashville, TN; 37209, Nashville, TN; 37201, Nashville, TN; 37203, Nashville, TN; 37212, Nashville, TN; 37219, Nashville, TN; 37208, Nashville, TN; 37204, Nashville, TN; 37211, Nashville, TN; 37210, Nashville, TN; 37217, Nashville, TN; 37218, Nashville, TN; 37214, Nashville, TN; 37205, Nashville, TN; 37215, Nashville, TN; 37213, Nashville, TN; 37027, Brentwood, TN; 37221, Nashville, TN"
MAX_PAGES = 2
UNIT_FALLBACK_COLUMNS = {"PRICE": "PRICE_1", "BEDS": "BEDS_1", "BATHROOMS": "BATHROOMS_1"}


def _ensure_priority_columns(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    columns = normalize_column_names(frame.columns)
    frame.columns = columns
    for target, fallback in UNIT_FALLBACK_COLUMNS.items():
        if target not in frame.columns and fallback in frame.columns:
            frame[target] = frame[fallback]
    return frame


def build_pipeline_dataframe(locations: Sequence[str], ingest_stamp: str) -> pd.DataFrame:
    config = FetchConfig(base_params=BASE_PARAMS, locations=locations, max_pages=MAX_PAGES)
    df_raw = fetch_dataframe(config)
    if df_raw.empty:
        return df_raw
    df_priority = _ensure_priority_columns(df_raw)
    df_priority["INGESTION_DATE"] = ingest_stamp
    return uppercase_dataframe(df_priority)


def main() -> None:
    try:
        locations = split_locations(RAW_LOCATIONS)
        frame = build_pipeline_dataframe(locations, ingestion_date)

        if frame.empty:
            logging.warning("No records fetched; aborting persistence steps.")
            return

        schema = load_schema(extra_columns=["INGESTION_DATE"])
        aligned = align_to_schema(frame, schema)

        ensure_table_exists(SQLITE_DB, TABLE_NAME, schema)
        persist_to_sqlite(aligned, SQLITE_DB, TABLE_NAME)
        csv_path = persist_to_csv(aligned)

        logging.info(f"SQLite table '{TABLE_NAME}' updated in {SQLITE_DB}.")
        logging.info(f"CSV exported to {csv_path}")
    except Exception as e:
        logging.error(f"An error occurred during execution: {e}")
        raise


if __name__ == "__main__":
    main()
