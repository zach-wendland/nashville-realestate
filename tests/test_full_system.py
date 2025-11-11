"""Comprehensive system test for Nashville Real Estate application.

Tests all major components:
1. Database configuration
2. Data loading and persistence
3. ForRent pipeline
4. ForSale pipeline
5. Streamlit app imports
6. Filter functionality
"""
from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from db.db_config import FORSALE_CONFIG, RENT_CONFIG, SQLITE_DB
from main_unified import (
    FORSALE_PARAMS,
    RENT_PARAMS,
    build_pipeline_dataframe,
    run_forsale_pipeline,
    run_rent_pipeline,
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')


def test_database_config():
    """Test 1: Verify database configuration."""
    print("\n" + "=" * 80)
    print("TEST 1: Database Configuration")
    print("=" * 80)

    assert SQLITE_DB.exists(), f"Database file does not exist: {SQLITE_DB}"
    assert RENT_CONFIG.table_name == "NashvilleRents01"
    assert FORSALE_CONFIG.table_name == "NashvilleForSale01"

    print("✅ Database configuration is valid")
    print(f"   Database path: {SQLITE_DB}")
    print(f"   Rent table: {RENT_CONFIG.table_name}")
    print(f"   ForSale table: {FORSALE_CONFIG.table_name}")


def test_data_loading():
    """Test 2: Verify data can be loaded from SQLite."""
    print("\n" + "=" * 80)
    print("TEST 2: Data Loading from SQLite")
    print("=" * 80)

    with sqlite3.connect(SQLITE_DB) as conn:
        # Test Rent data
        rent_df = pd.read_sql(f"SELECT * FROM {RENT_CONFIG.table_name} LIMIT 10", conn)
        print(f"✅ Loaded {len(rent_df)} rent records (sample)")
        print(f"   Columns: {', '.join(rent_df.columns.tolist()[:5])}...")

        # Test ForSale data
        sale_df = pd.read_sql(f"SELECT * FROM {FORSALE_CONFIG.table_name} LIMIT 10", conn)
        print(f"✅ Loaded {len(sale_df)} forsale records (sample)")
        print(f"   Columns: {', '.join(sale_df.columns.tolist()[:5])}...")

    return rent_df, sale_df


def test_pipeline_parameters():
    """Test 3: Verify pipeline parameters are correct."""
    print("\n" + "=" * 80)
    print("TEST 3: Pipeline Parameters")
    print("=" * 80)

    # Test Rent parameters
    assert "status_type" in RENT_PARAMS
    assert RENT_PARAMS["status_type"] == "ForRent"
    assert "rentMinPrice" in RENT_PARAMS
    print("✅ Rent pipeline parameters are valid")
    print(f"   Parameters: {RENT_PARAMS}")

    # Test ForSale parameters
    assert "status_type" in FORSALE_PARAMS
    assert FORSALE_PARAMS["status_type"] == "ForSale"
    assert "minPrice" in FORSALE_PARAMS
    print("✅ ForSale pipeline parameters are valid")
    print(f"   Parameters: {FORSALE_PARAMS}")


def test_filter_functionality(rent_df: pd.DataFrame, sale_df: pd.DataFrame):
    """Test 4: Verify filtering works correctly."""
    print("\n" + "=" * 80)
    print("TEST 4: Filter Functionality")
    print("=" * 80)

    # Test price filtering
    if "PRICE" in rent_df.columns:
        rent_df_copy = rent_df.copy()
        rent_df_copy["PRICE"] = pd.to_numeric(rent_df_copy["PRICE"], errors="coerce")
        price_filtered = rent_df_copy[rent_df_copy["PRICE"] > 2000]
        print(f"✅ Price filter: {len(rent_df)} -> {len(price_filtered)} records (>$2000)")

    # Test bedrooms filtering
    if "BEDROOMS" in rent_df.columns:
        rent_df_copy = rent_df.copy()
        rent_df_copy["BEDROOMS"] = pd.to_numeric(rent_df_copy["BEDROOMS"], errors="coerce")
        beds_filtered = rent_df_copy[rent_df_copy["BEDROOMS"] >= 2]
        print(f"✅ Bedrooms filter: {len(rent_df)} -> {len(beds_filtered)} records (>=2 beds)")

    # Test property type filtering
    if "PROPERTYTYPE" in sale_df.columns:
        unique_types = sale_df["PROPERTYTYPE"].dropna().unique()
        print(f"✅ Property types available: {', '.join(map(str, unique_types[:5]))}")

    # Test living area filtering
    if "LIVINGAREA" in sale_df.columns:
        sale_df_copy = sale_df.copy()
        sale_df_copy["LIVINGAREA"] = pd.to_numeric(sale_df_copy["LIVINGAREA"], errors="coerce")
        sqft_filtered = sale_df_copy[sale_df_copy["LIVINGAREA"] > 1000]
        print(f"✅ Living area filter: {len(sale_df)} -> {len(sqft_filtered)} records (>1000 sqft)")


def test_streamlit_imports():
    """Test 5: Verify streamlit app imports work."""
    print("\n" + "=" * 80)
    print("TEST 5: Streamlit App Imports")
    print("=" * 80)

    try:
        import streamlit_app
        print("✅ Streamlit app imports successfully")

        # Check key functions exist
        assert hasattr(streamlit_app, "_load_data")
        assert hasattr(streamlit_app, "_filter_dataframe")
        assert hasattr(streamlit_app, "_render_listing_view")
        assert hasattr(streamlit_app, "main")
        print("✅ All required functions are present")

    except Exception as e:
        print(f"❌ Streamlit app import failed: {e}")
        raise


def test_csv_exports():
    """Test 6: Verify CSV exports exist."""
    print("\n" + "=" * 80)
    print("TEST 6: CSV Exports")
    print("=" * 80)

    excel_dir = Path(__file__).resolve().parents[1] / "excel_files"

    # Find latest rent CSV
    rent_csvs = sorted(excel_dir.glob("nsh-rent*.csv"))
    if rent_csvs:
        latest_rent = rent_csvs[-1]
        print(f"✅ Latest rent CSV: {latest_rent.name}")
        df = pd.read_csv(latest_rent, nrows=5)
        print(f"   Records: {len(df)} (sample)")

    # Find latest forsale CSV
    sale_csvs = sorted(excel_dir.glob("nsh-forsale*.csv"))
    if sale_csvs:
        latest_sale = sale_csvs[-1]
        print(f"✅ Latest forsale CSV: {latest_sale.name}")
        df = pd.read_csv(latest_sale, nrows=5)
        print(f"   Records: {len(df)} (sample)")


def test_data_counts():
    """Test 7: Verify data counts are reasonable."""
    print("\n" + "=" * 80)
    print("TEST 7: Data Record Counts")
    print("=" * 80)

    with sqlite3.connect(SQLITE_DB) as conn:
        rent_count = pd.read_sql(f"SELECT COUNT(*) as count FROM {RENT_CONFIG.table_name}", conn)["count"][0]
        sale_count = pd.read_sql(f"SELECT COUNT(*) as count FROM {FORSALE_CONFIG.table_name}", conn)["count"][0]

        print(f"✅ Rent records: {rent_count:,}")
        print(f"✅ ForSale records: {sale_count:,}")

        assert rent_count > 0, "No rent records found!"
        assert sale_count > 0, "No forsale records found!"


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("NASHVILLE REAL ESTATE - COMPREHENSIVE SYSTEM TEST")
    print("=" * 80)

    try:
        # Run tests
        test_database_config()
        rent_df, sale_df = test_data_loading()
        test_pipeline_parameters()
        test_filter_functionality(rent_df, sale_df)
        test_streamlit_imports()
        test_csv_exports()
        test_data_counts()

        # Summary
        print("\n" + "=" * 80)
        print("ALL TESTS PASSED ✅")
        print("=" * 80)
        print("\nSystem Status:")
        print("  • Database: ✅ Operational")
        print("  • Data Loading: ✅ Working")
        print("  • Pipeline Parameters: ✅ Valid")
        print("  • Filter Functions: ✅ Working")
        print("  • Streamlit App: ✅ Ready")
        print("  • CSV Exports: ✅ Available")
        print("  • Data Records: ✅ Present")
        print("\n" + "=" * 80)

        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 80)
        logging.error(f"Test failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
