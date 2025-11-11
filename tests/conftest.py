"""Shared pytest fixtures for all tests."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

from db.db_migrator import PRIMARY_KEY_COLUMN, assign_primary_keys
from db.db_config import FORSALE_CONFIG, RENT_CONFIG, ListingConfig
from db.db_migrator_unified import ensure_table_exists, load_schema


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def mock_excel_schema(temp_dir: Path) -> Path:
    """Create a mock Excel schema file for testing."""
    schema_data = {
        "name": [
            "longitude",
            "latitude",
            "detailUrl",
            "price",
            "bedrooms",
            "bathrooms",
            "livingArea",
            "propertyType",
            "address",
            "optional_field",
        ],
        "needed?": ["Y", "Y", "Y", "Y", "Y", "Y", "Y", "Y", "Y", "N"],
    }
    df = pd.DataFrame(schema_data)
    excel_dir = temp_dir / "excel_files"
    excel_dir.mkdir(exist_ok=True)
    schema_path = excel_dir / "test-schema.xlsx"
    df.to_excel(schema_path, sheet_name="zillow-rent-schema", index=False)
    return schema_path


@pytest.fixture
def mock_db(temp_dir: Path) -> Path:
    """Create a temporary SQLite database for testing."""
    db_path = temp_dir / "test.db"
    return db_path


@pytest.fixture
def sample_zillow_response() -> Dict[str, Any]:
    """Sample Zillow API response for testing."""
    return {
        "results": [
            {
                "longitude": -86.7816,
                "latitude": 36.1627,
                "detailUrl": "https://www.zillow.com/homedetails/123-test-st",
                "price": 2000,
                "bedrooms": 2,
                "bathrooms": 2.0,
                "livingArea": 1200,
                "propertyType": "APARTMENT",
                "address": "123 Test St, Nashville, TN",
                "units": [
                    {"price": 2000, "beds": 2, "bathrooms": 2.0},
                    {"price": 2100, "beds": 2, "bathrooms": 2.0},
                ],
            },
            {
                "longitude": -86.7817,
                "latitude": 36.1628,
                "detailUrl": "https://www.zillow.com/homedetails/456-test-ave",
                "price": 1800,
                "bedrooms": 1,
                "bathrooms": 1.0,
                "livingArea": 800,
                "propertyType": "CONDO",
                "address": "456 Test Ave, Nashville, TN",
            },
        ],
        "totalPages": 2,
    }


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Sample DataFrame with rental listing data."""
    frame = pd.DataFrame(
        {
            "LONGITUDE": [-86.7816, -86.7817],
            "LATITUDE": [36.1627, 36.1628],
            "DETAILURL": [
                "https://www.zillow.com/homedetails/123-test-st",
                "https://www.zillow.com/homedetails/456-test-ave",
            ],
            "PRICE": [2000, 1800],
            "BEDROOMS": [2, 1],
            "BATHROOMS": [2.0, 1.0],
            "LIVINGAREA": [1200, 800],
            "PROPERTYTYPE": ["APARTMENT", "CONDO"],
            "ADDRESS": ["123 Test St, Nashville, TN", "456 Test Ave, Nashville, TN"],
        }
    )
    frame = assign_primary_keys(frame)
    return frame


@pytest.fixture
def sample_schema() -> pd.DataFrame:
    """Sample schema DataFrame."""
    return pd.DataFrame(
        {
            "name": [
                "LONGITUDE",
                "LATITUDE",
                "DETAILURL",
                "PRICE",
                "BEDROOMS",
                "BATHROOMS",
                "LIVINGAREA",
                "PROPERTYTYPE",
                "ADDRESS",
                PRIMARY_KEY_COLUMN,
            ]
        }
    )


@pytest.fixture
def rent_config() -> ListingConfig:
    """Rental listing configuration."""
    return RENT_CONFIG


@pytest.fixture
def forsale_config() -> ListingConfig:
    """For-sale listing configuration."""
    return FORSALE_CONFIG


@pytest.fixture
def dual_table_db(temp_dir: Path, sample_schema: pd.DataFrame) -> Path:
    """Create a database with both NashvilleRents01 and NashvilleForSale01 tables."""
    db_path = temp_dir / "dual_test.db"

    # Create both tables
    ensure_table_exists(db_path, RENT_CONFIG.table_name, sample_schema, RENT_CONFIG.unique_key_columns)
    ensure_table_exists(db_path, FORSALE_CONFIG.table_name, sample_schema, FORSALE_CONFIG.unique_key_columns)

    return db_path


@pytest.fixture
def legacy_table_db(temp_dir: Path, sample_schema: pd.DataFrame) -> Path:
    """Create a database with legacy table (no primary key) for migration testing."""
    db_path = temp_dir / "legacy_test.db"

    # Create table without primary key (old schema)
    schema_without_pk = sample_schema[sample_schema["name"] != PRIMARY_KEY_COLUMN].copy()
    col_defs = [f"{col} TEXT" for col in schema_without_pk["name"]]
    schema_sql = ", ".join(col_defs)

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(f"CREATE TABLE NashvilleRents01 ({schema_sql});")
        # Insert some legacy data
        conn.execute(
            "INSERT INTO NashvilleRents01 (DETAILURL, ADDRESS, PRICE) VALUES (?, ?, ?)",
            ("https://zillow.com/test1", "123 Main St", "2000")
        )
        conn.execute(
            "INSERT INTO NashvilleRents01 (DETAILURL, ADDRESS, PRICE) VALUES (?, ?, ?)",
            ("https://zillow.com/test2", "456 Oak Ave", "1800")
        )
        conn.commit()

    return db_path


@pytest.fixture
def sample_rent_data() -> pd.DataFrame:
    """Sample rental listing DataFrame."""
    return pd.DataFrame({
        "DETAILURL": [
            "HTTPS://WWW.ZILLOW.COM/HOMEDETAILS/123-TEST-ST",
            "HTTPS://WWW.ZILLOW.COM/HOMEDETAILS/456-TEST-AVE"
        ],
        "ADDRESS": ["123 TEST ST, NASHVILLE, TN", "456 TEST AVE, NASHVILLE, TN"],
        "PRICE": ["2000", "1800"],
        "BEDROOMS": ["2", "1"],
        "BATHROOMS": ["2.0", "1.0"],
        "INGESTION_DATE": ["20251110", "20251110"],
    })


@pytest.fixture
def sample_forsale_data() -> pd.DataFrame:
    """Sample for-sale listing DataFrame."""
    return pd.DataFrame({
        "DETAILURL": [
            "HTTPS://WWW.ZILLOW.COM/HOMEDETAILS/789-ELM-ST",
            "HTTPS://WWW.ZILLOW.COM/HOMEDETAILS/321-PINE-DR"
        ],
        "ADDRESS": ["789 ELM ST, NASHVILLE, TN", "321 PINE DR, NASHVILLE, TN"],
        "PRICE": ["350000", "425000"],
        "BEDROOMS": ["3", "4"],
        "BATHROOMS": ["2.0", "3.0"],
        "INGESTION_DATE": ["20251110", "20251110"],
    })
