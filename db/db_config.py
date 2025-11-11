from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

BASE_DIR = Path(__file__).resolve().parents[1]
EXCEL_DIR = BASE_DIR / "excel_files"
SCHEMA_FILE = EXCEL_DIR / "nashville-zillow-project.xlsx"
SCHEMA_SHEET = "zillow-rent-schema"
SQLITE_DB = BASE_DIR / "TESTRENT01.db"


@dataclass(frozen=True)
class ListingConfig:
    """Configuration for a specific listing type (Rent or ForSale)"""
    table_name: str
    csv_prefix: str
    unique_key_columns: Tuple[str, ...]


RENT_CONFIG = ListingConfig(
    table_name="NashvilleRents01",
    csv_prefix="nsh-rent",
    unique_key_columns=("DETAILURL",)
)

FORSALE_CONFIG = ListingConfig(
    table_name="NashvilleForSale01",
    csv_prefix="nsh-forsale",
    unique_key_columns=("ADDRESS",)
)

KEY_JOINER = "__||__"
PRIMARY_KEY_COLUMN = "RECORD_ID"
CSV_OUTPUT_DIR = EXCEL_DIR
