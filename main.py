from __future__ import annotations

import logging
from typing import List, Optional, Sequence

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from db.db_migrator import (
    SQLITE_DB,
    TABLE_NAME,
    align_to_schema,
    assign_primary_keys,
    ensure_table_exists,
    load_schema,
    normalize_column_names,
    persist_to_csv,
    persist_to_sqlite,
    PRIMARY_KEY_COLUMN,
    uppercase_dataframe,
)
from api.zillow_fetcher import FetchConfig, fetch_dataframe, split_locations
from utils.ingestionVars import ingestion_date

BASE_PARAMS = {
    "status_type": "ForRent",
    "rentMinPrice": 1600,
    "rentMaxPrice": 3300,
    "bedsMin": 1,
    "bedsMax": 4,
    "sqftMin": 700,
    "sqftMax": 3500
}
# RAW_LOCATIONS = "37206, Nashville, TN; 37216, Nashville, TN; 37207, Nashville, TN; 37209, Nashville, TN; Midtown, Nashville, TN; Brentwood, TN; Nashville, TN; Hendersonville, TN"
RAW_LOCATIONS = "37206, Nashville, TN; 37216, Nashville, TN; 37209, Nashville, TN; 37203, Nashville, TN; 37210, Nashville, TN; 37214, Nashville, TN; 37217, Nashville, TN; 37204, Nashville, TN; 37215, Nashville, TN; 37211, Nashville, TN; 37207, Nashville, TN; 37013, Nashville, TN; 37115, Nashville, TN; 37122, Nashville, TN;"
MAX_PAGES = 10
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
    normalized = uppercase_dataframe(df_priority)
    return assign_primary_keys(normalized)


def process_location_batch(locations: List[str], ingest_stamp: str) -> Optional[pd.DataFrame]:
    """Process a batch of locations and return the resulting DataFrame."""
    frame = build_pipeline_dataframe(locations, ingest_stamp)
    if frame.empty:
        logging.warning(f"No records fetched for locations: {', '.join(locations)}")
        return None
    return frame

def main() -> None:
    try:
        all_locations = split_locations(RAW_LOCATIONS)
        BATCH_SIZE = 5 
        all_frames = []
        
        for i in range(0, len(all_locations), BATCH_SIZE):
            batch = all_locations[i:i + BATCH_SIZE]
            logging.info(f"Processing batch {i//BATCH_SIZE + 1} of {(len(all_locations) + BATCH_SIZE - 1)//BATCH_SIZE}")
            batch_frame = process_location_batch(batch, ingestion_date)
            if batch_frame is not None:
                all_frames.append(batch_frame)
        
        if not all_frames:
            logging.warning("No records fetched from any batch; aborting persistence steps.")
            return
            
        frame = pd.concat(all_frames, ignore_index=True)

        schema = load_schema(extra_columns=["INGESTION_DATE", PRIMARY_KEY_COLUMN])
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
