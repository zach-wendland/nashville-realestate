"""Tests for unified database migrator supporting multiple listing types."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from db.db_config import FORSALE_CONFIG, PRIMARY_KEY_COLUMN, RENT_CONFIG
from db.db_migrator_unified import (
    _hash_with_fallback,
    assign_primary_keys,
    ensure_table_exists,
    persist_to_csv,
    persist_to_sqlite,
)


class TestEnsureTableExists:
    """Tests for ensure_table_exists with multi-listing support."""

    def test_creates_both_rent_and_forsale_tables(self, temp_dir, sample_schema):
        """Verify both NashvilleRents01 and NashvilleForSale01 tables are created."""
        db_path = temp_dir / "test.db"

        ensure_table_exists(db_path, RENT_CONFIG.table_name, sample_schema, RENT_CONFIG.unique_key_columns)
        ensure_table_exists(db_path, FORSALE_CONFIG.table_name, sample_schema, FORSALE_CONFIG.unique_key_columns)

        with sqlite3.connect(db_path) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = [t[0] for t in tables]

        assert RENT_CONFIG.table_name in table_names
        assert FORSALE_CONFIG.table_name in table_names

    def test_rent_table_has_detailurl_unique_index(self, temp_dir, sample_schema):
        """Verify rental table has unique index on DETAILURL."""
        db_path = temp_dir / "test.db"

        ensure_table_exists(db_path, RENT_CONFIG.table_name, sample_schema, RENT_CONFIG.unique_key_columns)

        with sqlite3.connect(db_path) as conn:
            indexes = conn.execute(f"PRAGMA index_list('{RENT_CONFIG.table_name}')").fetchall()
            index_names = [idx[1].lower() for idx in indexes]

        expected_index = f"ux_{RENT_CONFIG.table_name}_detailurl".lower()
        assert expected_index in index_names

    def test_forsale_table_has_address_unique_index(self, temp_dir, sample_schema):
        """Verify for-sale table has unique index on ADDRESS."""
        db_path = temp_dir / "test.db"

        ensure_table_exists(db_path, FORSALE_CONFIG.table_name, sample_schema, FORSALE_CONFIG.unique_key_columns)

        with sqlite3.connect(db_path) as conn:
            indexes = conn.execute(f"PRAGMA index_list('{FORSALE_CONFIG.table_name}')").fetchall()
            index_names = [idx[1].lower() for idx in indexes]

        expected_index = f"ux_{FORSALE_CONFIG.table_name}_address".lower()
        assert expected_index in index_names

    def test_both_tables_have_record_id_primary_key(self, dual_table_db):
        """Verify both tables have RECORD_ID as primary key."""
        with sqlite3.connect(dual_table_db) as conn:
            # Check rental table
            rent_info = conn.execute(f"PRAGMA table_info('{RENT_CONFIG.table_name}')").fetchall()
            rent_pk = [col for col in rent_info if col[5] == 1]  # col[5] is the pk flag
            assert len(rent_pk) == 1
            assert rent_pk[0][1] == PRIMARY_KEY_COLUMN

            # Check for-sale table
            sale_info = conn.execute(f"PRAGMA table_info('{FORSALE_CONFIG.table_name}')").fetchall()
            sale_pk = [col for col in sale_info if col[5] == 1]
            assert len(sale_pk) == 1
            assert sale_pk[0][1] == PRIMARY_KEY_COLUMN

    def test_rebuild_table_with_legacy_data_preserves_records(self, legacy_table_db, sample_schema):
        """Verify migration from legacy table preserves all data."""
        # Get count before migration
        with sqlite3.connect(legacy_table_db) as conn:
            count_before = conn.execute("SELECT COUNT(*) FROM NashvilleRents01").fetchone()[0]

        # Trigger migration by ensuring table exists with new schema
        ensure_table_exists(legacy_table_db, RENT_CONFIG.table_name, sample_schema, RENT_CONFIG.unique_key_columns)

        # Verify data preserved
        with sqlite3.connect(legacy_table_db) as conn:
            count_after = conn.execute("SELECT COUNT(*) FROM NashvilleRents01").fetchone()[0]
            # Check primary keys were assigned
            records = conn.execute("SELECT RECORD_ID, DETAILURL FROM NashvilleRents01").fetchall()

        assert count_after == count_before
        assert all(record[0] for record in records), "All records should have primary keys"

    def test_rebuild_assigns_primary_keys_from_unique_columns(self, legacy_table_db, sample_schema):
        """Verify migration assigns primary keys based on unique columns."""
        ensure_table_exists(legacy_table_db, RENT_CONFIG.table_name, sample_schema, RENT_CONFIG.unique_key_columns)

        with sqlite3.connect(legacy_table_db) as conn:
            records = conn.execute("SELECT RECORD_ID, DETAILURL FROM NashvilleRents01").fetchall()

        # All records should have non-empty primary keys
        assert all(record[0] and len(record[0]) > 0 for record in records)
        # Primary keys should be uppercase hex strings (SHA256)
        assert all(len(record[0]) == 64 for record in records)  # SHA256 hex length


class TestHashWithFallback:
    """Tests for _hash_with_fallback function."""

    def test_deterministic_for_same_input(self):
        """Same input should always produce same hash."""
        seed = "https://zillow.com/test"
        hash1 = _hash_with_fallback(seed)
        hash2 = _hash_with_fallback(seed)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_handles_empty_seed_with_fallback(self):
        """Empty seed should use fallback value."""
        hash_result = _hash_with_fallback("", "fallback123")

        assert hash_result
        assert len(hash_result) == 64

    def test_different_inputs_produce_different_hashes(self):
        """Different inputs should produce different hashes."""
        hash1 = _hash_with_fallback("https://zillow.com/test1")
        hash2 = _hash_with_fallback("https://zillow.com/test2")

        assert hash1 != hash2

    def test_case_insensitive(self):
        """Hash should be case insensitive (uppercase normalization)."""
        hash1 = _hash_with_fallback("test")
        hash2 = _hash_with_fallback("TEST")
        hash3 = _hash_with_fallback("TeSt")

        assert hash1 == hash2 == hash3


class TestAssignPrimaryKeys:
    """Tests for assign_primary_keys with configurable unique columns."""

    def test_assigns_keys_to_empty_dataframe(self):
        """Empty DataFrame should return empty without error."""
        df = pd.DataFrame()
        result = assign_primary_keys(df, ("DETAILURL",))

        assert result.empty

    def test_respects_existing_primary_keys(self, sample_rent_data):
        """Should not overwrite existing primary keys."""
        # Assign keys first time
        df_with_keys = assign_primary_keys(sample_rent_data.copy(), RENT_CONFIG.unique_key_columns)
        original_keys = df_with_keys[PRIMARY_KEY_COLUMN].tolist()

        # Assign again
        df_reassigned = assign_primary_keys(df_with_keys, RENT_CONFIG.unique_key_columns)
        new_keys = df_reassigned[PRIMARY_KEY_COLUMN].tolist()

        assert original_keys == new_keys

    def test_rent_keys_based_on_detailurl(self, sample_rent_data):
        """Rental keys should be based on DETAILURL."""
        df = assign_primary_keys(sample_rent_data, RENT_CONFIG.unique_key_columns)

        # Keys should be deterministic based on DETAILURL
        assert all(df[PRIMARY_KEY_COLUMN].notna())
        assert len(df[PRIMARY_KEY_COLUMN].unique()) == len(df)

    def test_forsale_keys_based_on_address(self, sample_forsale_data):
        """For-sale keys should be based on ADDRESS."""
        df = assign_primary_keys(sample_forsale_data, FORSALE_CONFIG.unique_key_columns)

        # Keys should be deterministic based on ADDRESS
        assert all(df[PRIMARY_KEY_COLUMN].notna())
        assert len(df[PRIMARY_KEY_COLUMN].unique()) == len(df)


class TestPersistToSqlite:
    """Tests for persist_to_sqlite with ListingConfig."""

    def test_creates_unique_index_per_config(self, dual_table_db, sample_rent_data, sample_forsale_data):
        """Each table should have unique index on its configured columns."""
        # Prepare data with primary keys
        rent_df = assign_primary_keys(sample_rent_data, RENT_CONFIG.unique_key_columns)
        sale_df = assign_primary_keys(sample_forsale_data, FORSALE_CONFIG.unique_key_columns)

        # Persist to both tables
        persist_to_sqlite(rent_df, RENT_CONFIG, dual_table_db)
        persist_to_sqlite(sale_df, FORSALE_CONFIG, dual_table_db)

        with sqlite3.connect(dual_table_db) as conn:
            # Check rental indexes
            rent_indexes = conn.execute(f"PRAGMA index_list('{RENT_CONFIG.table_name}')").fetchall()
            rent_index_names = [idx[1] for idx in rent_indexes]
            assert any("detailurl" in name.lower() for name in rent_index_names)

            # Check for-sale indexes
            sale_indexes = conn.execute(f"PRAGMA index_list('{FORSALE_CONFIG.table_name}')").fetchall()
            sale_index_names = [idx[1] for idx in sale_indexes]
            assert any("address" in name.lower() for name in sale_index_names)

    def test_data_segregated_between_tables(self, dual_table_db, sample_rent_data, sample_forsale_data):
        """Data should not leak between rental and for-sale tables."""
        rent_df = assign_primary_keys(sample_rent_data, RENT_CONFIG.unique_key_columns)
        sale_df = assign_primary_keys(sample_forsale_data, FORSALE_CONFIG.unique_key_columns)

        persist_to_sqlite(rent_df, RENT_CONFIG, dual_table_db)
        persist_to_sqlite(sale_df, FORSALE_CONFIG, dual_table_db)

        with sqlite3.connect(dual_table_db) as conn:
            rent_count = conn.execute(f"SELECT COUNT(*) FROM {RENT_CONFIG.table_name}").fetchone()[0]
            sale_count = conn.execute(f"SELECT COUNT(*) FROM {FORSALE_CONFIG.table_name}").fetchone()[0]

        assert rent_count == len(sample_rent_data)
        assert sale_count == len(sample_forsale_data)


class TestPersistToCSV:
    """Tests for persist_to_csv with configurable prefix."""

    def test_uses_config_prefix_for_rent(self, temp_dir, sample_rent_data):
        """CSV should use nsh-rent prefix for rental data."""
        from db.db_migrator_unified import CSV_OUTPUT_DIR

        # Temporarily override output dir
        import db.db_migrator_unified as migrator
        original_dir = migrator.CSV_OUTPUT_DIR
        migrator.CSV_OUTPUT_DIR = temp_dir

        try:
            csv_path = persist_to_csv(sample_rent_data, RENT_CONFIG.csv_prefix)
            assert "nsh-rent" in csv_path
        finally:
            migrator.CSV_OUTPUT_DIR = original_dir

    def test_uses_config_prefix_for_forsale(self, temp_dir, sample_forsale_data):
        """CSV should use nsh-forsale prefix for for-sale data."""
        import db.db_migrator_unified as migrator
        original_dir = migrator.CSV_OUTPUT_DIR
        migrator.CSV_OUTPUT_DIR = temp_dir

        try:
            csv_path = persist_to_csv(sample_forsale_data, FORSALE_CONFIG.csv_prefix)
            assert "nsh-forsale" in csv_path
        finally:
            migrator.CSV_OUTPUT_DIR = original_dir
