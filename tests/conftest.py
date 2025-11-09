"""Shared pytest fixtures for all tests."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

from db.db_migrator import PRIMARY_KEY_COLUMN, assign_primary_keys


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
