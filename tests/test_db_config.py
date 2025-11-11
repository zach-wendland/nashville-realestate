"""Tests for database configuration and initialization."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from db.db_config import (
    BASE_DIR,
    CSV_OUTPUT_DIR,
    EXCEL_DIR,
    FORSALE_CONFIG,
    KEY_JOINER,
    PRIMARY_KEY_COLUMN,
    RENT_CONFIG,
    SCHEMA_FILE,
    SQLITE_DB,
    ListingConfig,
)
from db.db_migrator_unified import load_schema
from init_db import init_all_tables


class TestListingConfig:
    """Tests for ListingConfig dataclass."""

    def test_listing_config_is_immutable(self, rent_config):
        """ListingConfig should be frozen and immutable."""
        with pytest.raises(AttributeError):
            rent_config.table_name = "Modified"

    def test_rent_config_has_correct_values(self, rent_config):
        """Verify rental configuration constants."""
        assert rent_config.table_name == "NashvilleRents01"
        assert rent_config.csv_prefix == "nsh-rent"
        assert rent_config.unique_key_columns == ("DETAILURL",)

    def test_forsale_config_has_correct_values(self, forsale_config):
        """Verify for-sale configuration constants."""
        assert forsale_config.table_name == "NashvilleForSale01"
        assert forsale_config.csv_prefix == "nsh-forsale"
        assert forsale_config.unique_key_columns == ("ADDRESS",)

    def test_configs_have_different_unique_columns(self, rent_config, forsale_config):
        """Rental and for-sale configs should have different unique key columns."""
        assert rent_config.unique_key_columns != forsale_config.unique_key_columns


class TestConfigConstants:
    """Tests for configuration constants."""

    def test_primary_key_column_constant(self):
        """Verify PRIMARY_KEY_COLUMN constant."""
        assert PRIMARY_KEY_COLUMN == "RECORD_ID"

    def test_key_joiner_constant(self):
        """Verify KEY_JOINER constant."""
        assert KEY_JOINER == "__||__"

    def test_base_dir_resolves_correctly(self):
        """Verify BASE_DIR points to project root."""
        assert BASE_DIR.exists()
        assert (BASE_DIR / "db").exists()

    def test_excel_dir_path(self):
        """Verify EXCEL_DIR path construction."""
        assert EXCEL_DIR == BASE_DIR / "excel_files"

    def test_schema_file_path(self):
        """Verify SCHEMA_FILE path construction."""
        expected_path = BASE_DIR / "excel_files" / "nashville-zillow-project.xlsx"
        assert SCHEMA_FILE == expected_path

    def test_sqlite_db_path(self):
        """Verify SQLITE_DB path points to TESTRENT01.db."""
        expected_path = BASE_DIR / "TESTRENT01.db"
        assert SQLITE_DB == expected_path

    def test_csv_output_dir_matches_excel_dir(self):
        """Verify CSV_OUTPUT_DIR is same as EXCEL_DIR."""
        assert CSV_OUTPUT_DIR == EXCEL_DIR


class TestInitDB:
    """Tests for init_db.py table initialization."""

    def test_init_all_tables_creates_both_tables(self, temp_dir, mock_excel_schema, monkeypatch):
        """init_all_tables should create both rental and for-sale tables."""
        test_db = temp_dir / "test_init.db"

        # Monkey patch the constants
        monkeypatch.setattr("init_db.SQLITE_DB", test_db)
        monkeypatch.setattr("db.db_migrator_unified.SQLITE_DB", test_db)
        monkeypatch.setattr("db.db_migrator_unified.SCHEMA_FILE", mock_excel_schema)

        # Run initialization
        init_all_tables()

        # Verify both tables exist
        with sqlite3.connect(test_db) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = [t[0] for t in tables]

        assert RENT_CONFIG.table_name in table_names
        assert FORSALE_CONFIG.table_name in table_names

    def test_init_all_tables_idempotent(self, temp_dir, mock_excel_schema, monkeypatch):
        """Running init_all_tables twice should not error."""
        test_db = temp_dir / "test_init.db"

        monkeypatch.setattr("init_db.SQLITE_DB", test_db)
        monkeypatch.setattr("db.db_migrator_unified.SQLITE_DB", test_db)
        monkeypatch.setattr("db.db_migrator_unified.SCHEMA_FILE", mock_excel_schema)

        # Run twice
        init_all_tables()
        init_all_tables()  # Should not raise

        # Verify tables still exist
        with sqlite3.connect(test_db) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()

        assert len(tables) == 2

    def test_init_preserves_existing_data(self, temp_dir, mock_excel_schema, monkeypatch):
        """Re-initializing should not delete existing data."""
        test_db = temp_dir / "test_init.db"

        monkeypatch.setattr("init_db.SQLITE_DB", test_db)
        monkeypatch.setattr("db.db_migrator_unified.SQLITE_DB", test_db)
        monkeypatch.setattr("db.db_migrator_unified.SCHEMA_FILE", mock_excel_schema)

        # Initialize and insert data
        init_all_tables()

        with sqlite3.connect(test_db) as conn:
            conn.execute(
                f"INSERT INTO {RENT_CONFIG.table_name} (DETAILURL, PRICE) VALUES (?, ?)",
                ("https://test.com", "2000")
            )
            conn.commit()
            count_before = conn.execute(f"SELECT COUNT(*) FROM {RENT_CONFIG.table_name}").fetchone()[0]

        # Re-initialize
        init_all_tables()

        # Verify data preserved
        with sqlite3.connect(test_db) as conn:
            count_after = conn.execute(f"SELECT COUNT(*) FROM {RENT_CONFIG.table_name}").fetchone()[0]

        assert count_after == count_before
