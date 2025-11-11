from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence, Any

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from db.db_migrator_unified import (
    align_to_schema,
    assign_primary_keys,
    ensure_table_exists,
    load_schema,
    normalize_column_names,
    persist_to_csv,
    persist_to_sqlite,
    uppercase_dataframe,
)
from db.db_config import (
    FORSALE_CONFIG,
    ListingConfig,
    PRIMARY_KEY_COLUMN,
    RENT_CONFIG,
    SQLITE_DB,
)
from api.zillow_fetcher import FetchConfig, fetch_dataframe, split_locations
from utils.ingestionVars import ingestion_date

RENT_PARAMS = {
    "status_type": "ForRent",
    "rentMinPrice": 1600,
    "rentMaxPrice": 3300,
    "bedsMin": 1,
    "bedsMax": 4,
    "sqftMin": 700,
    "sqftMax": 3500
}

FORSALE_PARAMS = {
    "status_type": "ForSale",
    # Removed home_type - too restrictive
    "minPrice": 200000,  # Verified working via diagnostic
    "maxPrice": 800000,  # Verified working via diagnostic
    "bedsMin": 2,
    "bedsMax": 5,
    # Removed bathsMin - use broader filter set
}

RAW_LOCATIONS = "37206, Nashville, TN; 37216, Nashville, TN; 37209, Nashville, TN; 37203, Nashville, TN; 37210, Nashville, TN; 37214, Nashville, TN; 37217, Nashville, TN; 37204, Nashville, TN; 37215, Nashville, TN; 37211, Nashville, TN; 37207, Nashville, TN; 37013, Nashville, TN; 37115, Nashville, TN; 37122, Nashville, TN;"
MAX_PAGES = 10
BATCH_SIZE = 5
UNIT_FALLBACK_COLUMNS = {"PRICE": "PRICE_1", "BEDS": "BEDS_1", "BATHROOMS": "BATHROOMS_1"}


def _ensure_priority_columns(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    columns = normalize_column_names(frame.columns)
    frame.columns = columns
    for target, fallback in UNIT_FALLBACK_COLUMNS.items():
        if target not in frame.columns and fallback in frame.columns:
            frame[target] = frame[fallback]
    return frame


def build_pipeline_dataframe(
    locations: Sequence[str],
    ingest_stamp: str,
    base_params: Dict[str, Any],
    config: ListingConfig,
    max_pages: int = MAX_PAGES
) -> pd.DataFrame:
    fetch_config = FetchConfig(base_params=base_params, locations=locations, max_pages=max_pages)
    df_raw = fetch_dataframe(fetch_config)
    if df_raw.empty:
        return df_raw
    df_priority = _ensure_priority_columns(df_raw)
    df_priority["INGESTION_DATE"] = ingest_stamp
    normalized = uppercase_dataframe(df_priority)
    return assign_primary_keys(normalized, config.unique_key_columns)


def process_location_batch(
    locations: List[str],
    ingest_stamp: str,
    base_params: Dict[str, Any],
    config: ListingConfig,
    max_pages: int = MAX_PAGES
) -> Optional[pd.DataFrame]:
    """Process a batch of locations and return the resulting DataFrame."""
    frame = build_pipeline_dataframe(locations, ingest_stamp, base_params, config, max_pages)
    if frame.empty:
        logging.warning(f"No records fetched for locations: {', '.join(locations)}")
        return None
    return frame


def run_pipeline(
    listing_config: ListingConfig,
    base_params: Dict[str, Any],
    locations_str: str = RAW_LOCATIONS,
    max_pages: int = MAX_PAGES,
    batch_size: int = BATCH_SIZE
) -> None:
    """Run the data pipeline for a specific listing type."""
    try:
        logging.info(f"Starting pipeline for {listing_config.table_name}")
        all_locations = split_locations(locations_str)
        all_frames = []

        for i in range(0, len(all_locations), batch_size):
            batch = all_locations[i:i + batch_size]
            logging.info(f"Processing batch {i//batch_size + 1} of {(len(all_locations) + batch_size - 1)//batch_size}")
            batch_frame = process_location_batch(batch, ingestion_date, base_params, listing_config, max_pages)
            if batch_frame is not None:
                all_frames.append(batch_frame)

        if not all_frames:
            logging.warning("No records fetched from any batch; aborting persistence steps.")
            return

        frame = pd.concat(all_frames, ignore_index=True)

        schema = load_schema(extra_columns=["INGESTION_DATE", PRIMARY_KEY_COLUMN])
        aligned = align_to_schema(frame, schema)

        ensure_table_exists(SQLITE_DB, listing_config.table_name, schema, listing_config.unique_key_columns)
        persist_to_sqlite(aligned, listing_config, SQLITE_DB)
        csv_path = persist_to_csv(aligned, listing_config.csv_prefix)

        logging.info(f"SQLite table '{listing_config.table_name}' updated in {SQLITE_DB}.")
        logging.info(f"CSV exported to {csv_path}")
    except Exception as e:
        logging.error(f"An error occurred during {listing_config.table_name} pipeline execution: {e}")
        raise


def run_rent_pipeline() -> None:
    """Run the rental listings pipeline."""
    run_pipeline(RENT_CONFIG, RENT_PARAMS)


def run_forsale_pipeline() -> None:
    """Run the for-sale listings pipeline."""
    run_pipeline(FORSALE_CONFIG, FORSALE_PARAMS)


def run_all_pipelines() -> None:
    """Run both rental and for-sale pipelines."""
    logging.info("=" * 80)
    logging.info("Running Rental Listings Pipeline")
    logging.info("=" * 80)
    run_rent_pipeline()

    logging.info("")
    logging.info("=" * 80)
    logging.info("Running For-Sale Listings Pipeline")
    logging.info("=" * 80)
    run_forsale_pipeline()

    logging.info("")
    logging.info("=" * 80)
    logging.info("All pipelines completed successfully!")
    logging.info("=" * 80)


def main() -> None:
    run_all_pipelines()


if __name__ == "__main__":
    main()
