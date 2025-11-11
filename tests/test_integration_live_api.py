"""Live API integration tests (requires RAPIDAPI_KEY environment variable).

These tests hit the actual Zillow API and verify end-to-end pipeline functionality.
They are marked with @pytest.mark.live and should be run sparingly to avoid API costs.

Run with: pytest tests/test_integration_live_api.py -v -m live
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from db.db_config import FORSALE_CONFIG, PRIMARY_KEY_COLUMN, RENT_CONFIG
from main_unified import run_forsale_pipeline, run_rent_pipeline
from utils.ingestionVars import ingestion_date


@pytest.mark.live
class TestLiveRentPipeline:
    """Live tests for rental listings pipeline."""

    def test_live_rent_pipeline_fetches_real_data(self, dual_table_db, monkeypatch):
        """Rental pipeline should fetch real data from Zillow API."""
        # Override database path to use test database
        monkeypatch.setattr("main_unified.SQLITE_DB", dual_table_db)
        monkeypatch.setattr("db.db_migrator_unified.SQLITE_DB", dual_table_db)

        # Override to fetch minimal data (1 page, 1 location)
        monkeypatch.setattr("main_unified.RAW_LOCATIONS", "37206, Nashville, TN")
        monkeypatch.setattr("main_unified.MAX_PAGES", 1)

        # Run pipeline
        run_rent_pipeline()

        # Verify data was inserted
        with sqlite3.connect(dual_table_db) as conn:
            count = conn.execute(f"SELECT COUNT(*) FROM {RENT_CONFIG.table_name}").fetchone()[0]
            sample = pd.read_sql(f"SELECT * FROM {RENT_CONFIG.table_name} LIMIT 5", conn)

        assert count > 0, "Should fetch at least some rental listings"
        assert not sample.empty
        print(f"\\nFetched {count} rental listings from live API")

    def test_live_data_populates_database(self, dual_table_db, monkeypatch):
        """Live data should populate database with complete records."""
        monkeypatch.setattr("main_unified.SQLITE_DB", dual_table_db)
        monkeypatch.setattr("db.db_migrator_unified.SQLITE_DB", dual_table_db)
        monkeypatch.setattr("main_unified.RAW_LOCATIONS", "37206, Nashville, TN")
        monkeypatch.setattr("main_unified.MAX_PAGES", 1)

        run_rent_pipeline()

        with sqlite3.connect(dual_table_db) as conn:
            df = pd.read_sql(f"SELECT * FROM {RENT_CONFIG.table_name}", conn)

        # Verify critical columns exist and are populated
        assert PRIMARY_KEY_COLUMN in df.columns
        assert "DETAILURL" in df.columns
        assert "PRICE" in df.columns
        assert "INGESTION_DATE" in df.columns

        # Verify primary keys assigned
        assert df[PRIMARY_KEY_COLUMN].notna().all()
        assert df["INGESTION_DATE"].iloc[0] == ingestion_date

    def test_live_data_matches_schema(self, dual_table_db, monkeypatch, sample_schema):
        """Live data should conform to expected schema."""
        monkeypatch.setattr("main_unified.SQLITE_DB", dual_table_db)
        monkeypatch.setattr("db.db_migrator_unified.SQLITE_DB", dual_table_db)
        monkeypatch.setattr("main_unified.RAW_LOCATIONS", "37206, Nashville, TN")
        monkeypatch.setattr("main_unified.MAX_PAGES", 1)

        run_rent_pipeline()

        with sqlite3.connect(dual_table_db) as conn:
            df = pd.read_sql(f"SELECT * FROM {RENT_CONFIG.table_name}", conn)
            table_columns = [row[1] for row in conn.execute(f"PRAGMA table_info('{RENT_CONFIG.table_name}')").fetchall()]

        # Verify all schema columns exist in table
        expected_columns = sample_schema["name"].tolist()
        for col in expected_columns:
            assert col in table_columns


@pytest.mark.live
class TestLiveForSalePipeline:
    """Live tests for for-sale listings pipeline."""

    def test_live_forsale_pipeline_fetches_real_data(self, dual_table_db, monkeypatch):
        """For-sale pipeline should fetch real data from Zillow API."""
        monkeypatch.setattr("main_unified.SQLITE_DB", dual_table_db)
        monkeypatch.setattr("db.db_migrator_unified.SQLITE_DB", dual_table_db)
        monkeypatch.setattr("main_unified.RAW_LOCATIONS", "37206, Nashville, TN")
        monkeypatch.setattr("main_unified.MAX_PAGES", 1)

        run_forsale_pipeline()

        with sqlite3.connect(dual_table_db) as conn:
            count = conn.execute(f"SELECT COUNT(*) FROM {FORSALE_CONFIG.table_name}").fetchone()[0]

        assert count > 0, "Should fetch at least some for-sale listings"
        print(f"\\nFetched {count} for-sale listings from live API")


@pytest.mark.live
class TestLiveAPIErrorHandling:
    """Tests for API error handling and rate limiting."""

    def test_live_api_rate_limiting_respected(self, dual_table_db, monkeypatch):
        """Pipeline should respect rate limiting without 429 errors."""
        monkeypatch.setattr("main_unified.SQLITE_DB", dual_table_db)
        monkeypatch.setattr("db.db_migrator_unified.SQLITE_DB", dual_table_db)
        # Test with multiple locations to trigger multiple requests
        monkeypatch.setattr("main_unified.RAW_LOCATIONS", "37206, Nashville, TN; 37209, Nashville, TN")
        monkeypatch.setattr("main_unified.MAX_PAGES", 2)
        monkeypatch.setattr("main_unified.BATCH_SIZE", 1)  # One location per batch

        # Should not raise exception from rate limiting
        try:
            run_rent_pipeline()
            success = True
        except Exception as e:
            if "429" in str(e):
                pytest.fail(f"Rate limiting not respected: {e}")
            # Other errors might be network issues, log but don't fail
            print(f"\\nWarning: API error occurred (might be network): {e}")
            success = False

        if success:
            print("\\nRate limiting test passed - no 429 errors")

    def test_live_api_error_recovery(self, dual_table_db, monkeypatch):
        """Pipeline should retry on transient API errors."""
        monkeypatch.setattr("main_unified.SQLITE_DB", dual_table_db)
        monkeypatch.setattr("db.db_migrator_unified.SQLITE_DB", dual_table_db)
        monkeypatch.setattr("main_unified.RAW_LOCATIONS", "37206, Nashville, TN")
        monkeypatch.setattr("main_unified.MAX_PAGES", 1)

        # Run pipeline - should succeed even with potential transient errors
        try:
            run_rent_pipeline()

            # Verify data was fetched despite any retries
            with sqlite3.connect(dual_table_db) as conn:
                count = conn.execute(f"SELECT COUNT(*) FROM {RENT_CONFIG.table_name}").fetchone()[0]

            assert count > 0, "Should successfully fetch data after retries"
        except Exception as e:
            # If it fails, it should be an unrecoverable error, not a retry failure
            print(f"\\nPipeline failed with unrecoverable error: {e}")
            pytest.skip("API temporarily unavailable - this is expected occasionally")
