"""Tests for primary key generation with deterministic hashing."""
from __future__ import annotations

import pandas as pd
import pytest

from db.db_config import FORSALE_CONFIG, PRIMARY_KEY_COLUMN, RENT_CONFIG
from db.db_migrator_unified import (
    _build_primary_key_seed,
    _hash_with_fallback,
    assign_primary_keys,
)


class TestPrimaryKeyGeneration:
    """Tests for deterministic primary key generation."""

    def test_primary_key_from_detailurl_deterministic(self):
        """Same DETAILURL should always produce same primary key."""
        df1 = pd.DataFrame({
            "DETAILURL": ["HTTPS://WWW.ZILLOW.COM/TEST"],
            "ADDRESS": ["123 MAIN ST"]
        })
        df2 = pd.DataFrame({
            "DETAILURL": ["HTTPS://WWW.ZILLOW.COM/TEST"],
            "ADDRESS": ["456 OAK AVE"]  # Different address
        })

        result1 = assign_primary_keys(df1, RENT_CONFIG.unique_key_columns)
        result2 = assign_primary_keys(df2, RENT_CONFIG.unique_key_columns)

        # Same DETAILURL → same key (address doesn't matter for rent config)
        assert result1[PRIMARY_KEY_COLUMN].iloc[0] == result2[PRIMARY_KEY_COLUMN].iloc[0]

    def test_primary_key_from_address_deterministic(self):
        """Same ADDRESS should always produce same primary key."""
        df1 = pd.DataFrame({
            "DETAILURL": ["HTTPS://WWW.ZILLOW.COM/TEST1"],
            "ADDRESS": ["123 MAIN ST, NASHVILLE, TN"]
        })
        df2 = pd.DataFrame({
            "DETAILURL": ["HTTPS://WWW.ZILLOW.COM/TEST2"],  # Different URL
            "ADDRESS": ["123 MAIN ST, NASHVILLE, TN"]
        })

        result1 = assign_primary_keys(df1, FORSALE_CONFIG.unique_key_columns)
        result2 = assign_primary_keys(df2, FORSALE_CONFIG.unique_key_columns)

        # Same ADDRESS → same key (URL doesn't matter for forsale config)
        assert result1[PRIMARY_KEY_COLUMN].iloc[0] == result2[PRIMARY_KEY_COLUMN].iloc[0]

    def test_primary_key_different_for_different_inputs(self):
        """Different inputs should produce different primary keys."""
        df = pd.DataFrame({
            "DETAILURL": [
                "HTTPS://WWW.ZILLOW.COM/TEST1",
                "HTTPS://WWW.ZILLOW.COM/TEST2"
            ],
            "ADDRESS": ["123 MAIN ST", "456 OAK AVE"]
        })

        result = assign_primary_keys(df, RENT_CONFIG.unique_key_columns)
        keys = result[PRIMARY_KEY_COLUMN].tolist()

        assert keys[0] != keys[1]
        assert len(set(keys)) == 2  # All unique

    def test_primary_key_handles_unicode_addresses(self):
        """Unicode characters in addresses should be handled correctly."""
        df = pd.DataFrame({
            "ADDRESS": ["123 RUE DES ÉGLISES, MONTRÉAL", "456 STRASSE, MÜNCHEN"],
            "DETAILURL": ["URL1", "URL2"]
        })

        result = assign_primary_keys(df, FORSALE_CONFIG.unique_key_columns)

        assert all(result[PRIMARY_KEY_COLUMN].notna())
        assert all(len(key) == 64 for key in result[PRIMARY_KEY_COLUMN])

    def test_primary_key_handles_special_characters(self):
        """Special characters should be handled without SQL injection risk."""
        df = pd.DataFrame({
            "DETAILURL": [
                "HTTPS://TEST.COM/PATH?PARAM=VALUE&OTHER=1",
                "HTTPS://TEST.COM/PATH';DROP TABLE--"
            ],
            "ADDRESS": ["NORMAL ADDRESS", "ADDRESS WITH 'QUOTES'"]
        })

        result = assign_primary_keys(df, RENT_CONFIG.unique_key_columns)

        assert all(result[PRIMARY_KEY_COLUMN].notna())
        assert all(len(key) == 64 for key in result[PRIMARY_KEY_COLUMN])
        # Should be uppercase hex (A-F0-9)
        assert all(key.isupper() and all(c in "0123456789ABCDEF" for c in key)
                   for key in result[PRIMARY_KEY_COLUMN])

    def test_primary_key_fallback_to_rowid(self):
        """When unique column is empty, should use fallback (rowid)."""
        df = pd.DataFrame({
            "DETAILURL": ["", ""],
            "ADDRESS": ["123 MAIN ST", "456 OAK AVE"]
        })

        result = assign_primary_keys(df, RENT_CONFIG.unique_key_columns)

        # Should still assign keys using fallback mechanism
        assert all(result[PRIMARY_KEY_COLUMN].notna())
        # Keys should be different even though DETAILURL is empty
        assert result[PRIMARY_KEY_COLUMN].iloc[0] != result[PRIMARY_KEY_COLUMN].iloc[1]

    def test_primary_key_uppercase_normalization(self):
        """Primary key generation should be case insensitive."""
        df1 = pd.DataFrame({"DETAILURL": ["https://test.com"], "ADDRESS": ["address"]})
        df2 = pd.DataFrame({"DETAILURL": ["HTTPS://TEST.COM"], "ADDRESS": ["ADDRESS"]})
        df3 = pd.DataFrame({"DETAILURL": ["HtTpS://TeSt.CoM"], "ADDRESS": ["AdDrEsS"]})

        result1 = assign_primary_keys(df1, RENT_CONFIG.unique_key_columns)
        result2 = assign_primary_keys(df2, RENT_CONFIG.unique_key_columns)
        result3 = assign_primary_keys(df3, RENT_CONFIG.unique_key_columns)

        # All should produce same key
        assert result1[PRIMARY_KEY_COLUMN].iloc[0] == result2[PRIMARY_KEY_COLUMN].iloc[0]
        assert result2[PRIMARY_KEY_COLUMN].iloc[0] == result3[PRIMARY_KEY_COLUMN].iloc[0]

    def test_existing_keys_not_overwritten(self):
        """Existing primary keys should not be overwritten."""
        df = pd.DataFrame({
            "DETAILURL": ["URL1", "URL2"],
            "ADDRESS": ["ADDR1", "ADDR2"],
            PRIMARY_KEY_COLUMN: ["EXISTING_KEY_1", ""]  # One existing, one empty
        })

        result = assign_primary_keys(df, RENT_CONFIG.unique_key_columns)

        # First key should be preserved
        assert result[PRIMARY_KEY_COLUMN].iloc[0] == "EXISTING_KEY_1"
        # Second key should be assigned
        assert result[PRIMARY_KEY_COLUMN].iloc[1] != ""
        assert len(result[PRIMARY_KEY_COLUMN].iloc[1]) == 64


class TestHashCollisionProbability:
    """Property-based tests for hash collision avoidance."""

    def test_hash_collision_probability_with_large_dataset(self):
        """Test collision avoidance with 10,000 records."""
        # Generate 10,000 unique URLs
        df = pd.DataFrame({
            "DETAILURL": [f"HTTPS://WWW.ZILLOW.COM/PROPERTY-{i}" for i in range(10000)],
            "ADDRESS": [f"{i} MAIN ST" for i in range(10000)]
        })

        result = assign_primary_keys(df, RENT_CONFIG.unique_key_columns)
        keys = result[PRIMARY_KEY_COLUMN]

        # Verify no collisions
        assert len(keys) == len(keys.unique())
        assert keys.notna().all()

    def test_hash_seed_construction_with_multiple_columns(self):
        """Test _build_primary_key_seed with compound keys."""
        df = pd.DataFrame({
            "COL1": ["A", "B"],
            "COL2": ["X", "Y"],
            "COL3": ["1", "2"]
        })

        seed = _build_primary_key_seed(df, ("COL1", "COL2", "COL3"))

        # Should join with KEY_JOINER
        assert "__||__" in seed.iloc[0]
        # Should be uppercase
        assert seed.iloc[0].isupper()
        # Should be deterministic
        seed2 = _build_primary_key_seed(df, ("COL1", "COL2", "COL3"))
        assert seed.equals(seed2)
