"""Initialize database tables for both Rental and ForSale listings."""
from __future__ import annotations

import logging

from db.db_config import FORSALE_CONFIG, PRIMARY_KEY_COLUMN, RENT_CONFIG, SQLITE_DB
from db.db_migrator_unified import ensure_table_exists, load_schema

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def init_all_tables() -> None:
    """Create all required tables in the database if they don't exist."""
    schema = load_schema(extra_columns=["INGESTION_DATE", PRIMARY_KEY_COLUMN])

    # Create Rentals table
    logging.info(f"Ensuring {RENT_CONFIG.table_name} table exists...")
    ensure_table_exists(SQLITE_DB, RENT_CONFIG.table_name, schema, RENT_CONFIG.unique_key_columns)
    logging.info(f"✓ {RENT_CONFIG.table_name} table ready")

    # Create ForSale table
    logging.info(f"Ensuring {FORSALE_CONFIG.table_name} table exists...")
    ensure_table_exists(SQLITE_DB, FORSALE_CONFIG.table_name, schema, FORSALE_CONFIG.unique_key_columns)
    logging.info(f"✓ {FORSALE_CONFIG.table_name} table ready")

    logging.info(f"\n✓ All tables initialized in {SQLITE_DB}")


if __name__ == "__main__":
    init_all_tables()
