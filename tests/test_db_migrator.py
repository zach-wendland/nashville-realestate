"""Comprehensive tests for db/db_migrator.py module."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from db.db_migrator import (
    KEY_JOINER,
    UNIQUE_KEY_COLUMNS,
    _build_key_series,
    _ensure_unique_index,
    align_to_schema,
    build_sql_schema,
    ensure_table_exists,
    load_schema,
    normalize_column_names,
    persist_to_csv,
    persist_to_sqlite,
    uppercase_dataframe,
)


class TestNormalizeColumnNames:
    """Tests for normalize_column_names function."""

    def test_normalize_column_names_uppercase_conversion(self):
        """Test that column names are converted to uppercase."""
        columns = ["name", "Price", "Address"]
        result = normalize_column_names(columns)
        assert result == ["NAME", "PRICE", "ADDRESS"]

    def test_normalize_column_names_replaces_dots_with_double_underscore(self):
        """Test that dots are replaced with double underscores."""
        columns = ["address.street", "location.lat"]
        result = normalize_column_names(columns)
        assert result == ["ADDRESS__STREET", "LOCATION__LAT"]

    def test_normalize_column_names_strips_whitespace(self):
        """Test that whitespace is stripped from column names."""
        columns = ["  name  ", " price ", "address "]
        result = normalize_column_names(columns)
        assert result == ["NAME", "PRICE", "ADDRESS"]

    def test_normalize_column_names_handles_duplicates(self):
        """Test that duplicate column names get numeric suffixes."""
        columns = ["name", "name", "name", "price"]
        result = normalize_column_names(columns)
        assert result == ["NAME", "NAME_1", "NAME_2", "PRICE"]

    def test_normalize_column_names_handles_numeric_input(self):
        """Test that numeric column names are converted to strings."""
        columns = [1, 2, 3]
        result = normalize_column_names(columns)
        assert result == ["1", "2", "3"]

    def test_normalize_column_names_empty_list(self):
        """Test that empty list returns empty list."""
        assert normalize_column_names([]) == []

    def test_normalize_column_names_preserves_order(self):
        """Test that column order is preserved."""
        columns = ["zebra", "alpha", "beta"]
        result = normalize_column_names(columns)
        assert result == ["ZEBRA", "ALPHA", "BETA"]


class TestUppercaseDataFrame:
    """Tests for uppercase_dataframe function."""

    def test_uppercase_dataframe_converts_strings(self):
        """Test that string values are converted to uppercase."""
        df = pd.DataFrame({"name": ["Alice", "bob"], "city": ["Nashville", "atlanta"]})
        result = uppercase_dataframe(df)
        assert result["name"].tolist() == ["ALICE", "BOB"]
        assert result["city"].tolist() == ["NASHVILLE", "ATLANTA"]

    def test_uppercase_dataframe_converts_numbers_to_strings(self):
        """Test that numeric values are converted to uppercase strings."""
        df = pd.DataFrame({"price": [2000, 1500], "beds": [2, 1]})
        result = uppercase_dataframe(df)
        assert result["price"].tolist() == ["2000", "1500"]
        assert result["beds"].tolist() == ["2", "1"]

    def test_uppercase_dataframe_handles_nan_as_empty_string(self):
        """Test that NaN values are converted to empty strings."""
        df = pd.DataFrame({"name": ["Alice", None, pd.NA], "price": [2000, pd.NA, 1500]})
        result = uppercase_dataframe(df)
        assert result["name"].tolist() == ["ALICE", "", ""]
        assert result["price"].tolist() == ["2000", "", "1500"]

    def test_uppercase_dataframe_empty_dataframe(self):
        """Test that empty DataFrame returns empty DataFrame."""
        df = pd.DataFrame()
        result = uppercase_dataframe(df)
        assert result.empty

    def test_uppercase_dataframe_preserves_shape(self):
        """Test that DataFrame shape is preserved."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
        result = uppercase_dataframe(df)
        assert result.shape == df.shape


class TestLoadSchema:
    """Tests for load_schema function."""

    def test_load_schema_loads_required_columns(self, mock_excel_schema):
        """Test that required columns are loaded from schema file."""
        schema = load_schema(path=mock_excel_schema)
        assert "name" in schema.columns
        assert len(schema) > 0
        # All loaded columns should be required (needed? = Y)
        expected = [
            "LONGITUDE",
            "LATITUDE",
            "DETAILURL",
            "PRICE",
            "BEDROOMS",
            "BATHROOMS",
            "LIVINGAREA",
            "PROPERTYTYPE",
            "ADDRESS",
        ]
        assert schema["name"].tolist() == expected

    def test_load_schema_with_extra_columns(self, mock_excel_schema):
        """Test adding extra columns to schema."""
        schema = load_schema(path=mock_excel_schema, extra_columns=["INGESTION_DATE", "SOURCE"])
        assert "INGESTION_DATE" in schema["name"].values
        assert "SOURCE" in schema["name"].values

    def test_load_schema_extra_columns_no_duplicates(self, mock_excel_schema):
        """Test that duplicate columns in extra_columns are removed."""
        schema = load_schema(
            path=mock_excel_schema, extra_columns=["PRICE", "INGESTION_DATE", "PRICE"]
        )
        # PRICE already exists in required columns, should not be duplicated
        price_count = (schema["name"] == "PRICE").sum()
        assert price_count == 1

    def test_load_schema_normalizes_column_names(self, mock_excel_schema):
        """Test that schema column names are normalized."""
        schema = load_schema(path=mock_excel_schema)
        # All names should be uppercase
        assert all(name.isupper() for name in schema["name"])

    def test_load_schema_raises_for_missing_file(self):
        """Test that FileNotFoundError is raised for missing schema file."""
        with pytest.raises(FileNotFoundError, match="Schema file not found"):
            load_schema(path="/nonexistent/schema.xlsx")


class TestAlignToSchema:
    """Tests for align_to_schema function."""

    def test_align_to_schema_reorders_columns(self, sample_schema):
        """Test that DataFrame columns are reordered to match schema."""
        df = pd.DataFrame(
            {"ADDRESS": ["123 Main"], "PRICE": [2000], "DETAILURL": ["http://test"]}
        )
        result = align_to_schema(df, sample_schema)
        # Result columns should match schema order
        assert list(result.columns) == sample_schema["name"].tolist()

    def test_align_to_schema_adds_missing_columns(self, sample_schema):
        """Test that missing columns are added with empty string fill value."""
        df = pd.DataFrame({"PRICE": [2000], "DETAILURL": ["http://test"]})
        result = align_to_schema(df, sample_schema)
        assert "ADDRESS" in result.columns
        assert "LONGITUDE" in result.columns
        # Missing columns should have empty string values
        assert result["ADDRESS"].iloc[0] == ""

    def test_align_to_schema_removes_extra_columns(self, sample_schema):
        """Test that columns not in schema are removed."""
        df = pd.DataFrame(
            {
                "PRICE": [2000],
                "EXTRA_COLUMN": ["value"],
                "ANOTHER_EXTRA": [123],
                "DETAILURL": ["http://test"],
            }
        )
        result = align_to_schema(df, sample_schema)
        assert "EXTRA_COLUMN" not in result.columns
        assert "ANOTHER_EXTRA" not in result.columns

    def test_align_to_schema_normalizes_input_columns(self, sample_schema):
        """Test that input column names are normalized before alignment."""
        df = pd.DataFrame({"price": [2000], "detail url": ["http://test"]})
        result = align_to_schema(df, sample_schema)
        # Should work despite lowercase and spaces
        assert "PRICE" in result.columns


class TestPersistToCSV:
    """Tests for persist_to_csv function."""

    def test_persist_to_csv_creates_file(self, sample_dataframe, temp_dir, monkeypatch):
        """Test that CSV file is created."""
        # Mock the CSV_OUTPUT_DIR and BASE_DIR
        monkeypatch.setattr("db.db_migrator.CSV_OUTPUT_DIR", temp_dir)
        csv_path = persist_to_csv(sample_dataframe)
        assert Path(csv_path).exists()

    def test_persist_to_csv_uses_date_in_filename(self, sample_dataframe, temp_dir, monkeypatch):
        """Test that filename includes current date in YYYYMMDD format."""
        monkeypatch.setattr("db.db_migrator.CSV_OUTPUT_DIR", temp_dir)
        csv_path = persist_to_csv(sample_dataframe)
        filename = Path(csv_path).name
        # Should match pattern nsh-rentYYYYMMDD.csv
        assert filename.startswith("nsh-rent")
        assert filename.endswith(".csv")
        # Extract date portion
        date_str = filename[8:-4]  # Remove 'nsh-rent' and '.csv'
        assert len(date_str) == 8  # YYYYMMDD
        assert date_str.isdigit()

    def test_persist_to_csv_content_matches_dataframe(
        self, sample_dataframe, temp_dir, monkeypatch
    ):
        """Test that CSV content matches DataFrame."""
        monkeypatch.setattr("db.db_migrator.CSV_OUTPUT_DIR", temp_dir)
        csv_path = persist_to_csv(sample_dataframe)
        loaded_df = pd.read_csv(csv_path)
        assert len(loaded_df) == len(sample_dataframe)
        assert list(loaded_df.columns) == list(sample_dataframe.columns)

    def test_persist_to_csv_creates_directory_if_missing(self, sample_dataframe, temp_dir):
        """Test that output directory is created if it doesn't exist."""
        import db.db_migrator as db_module

        new_dir = temp_dir / "new_directory"
        original_dir = db_module.CSV_OUTPUT_DIR
        try:
            db_module.CSV_OUTPUT_DIR = new_dir
            assert not new_dir.exists()
            persist_to_csv(sample_dataframe)
            assert new_dir.exists()
        finally:
            db_module.CSV_OUTPUT_DIR = original_dir


class TestBuildSQLSchema:
    """Tests for build_sql_schema function."""

    def test_build_sql_schema_creates_text_columns(self, sample_schema):
        """Test that SQL schema creates TEXT columns."""
        sql = build_sql_schema(sample_schema)
        assert "LONGITUDE TEXT" in sql
        assert "LATITUDE TEXT" in sql
        assert "PRICE TEXT" in sql

    def test_build_sql_schema_comma_separated(self, sample_schema):
        """Test that columns are comma-separated."""
        sql = build_sql_schema(sample_schema)
        column_count = sample_schema["name"].count()
        comma_count = sql.count(",")
        assert comma_count == column_count - 1

    def test_build_sql_schema_empty_schema(self):
        """Test with empty schema."""
        schema = pd.DataFrame({"name": []})
        sql = build_sql_schema(schema)
        assert sql == ""


class TestEnsureUniqueIndex:
    """Tests for _ensure_unique_index function."""

    def test_ensure_unique_index_creates_index(self, mock_db):
        """Test that unique index is created on specified columns."""
        with sqlite3.connect(str(mock_db)) as conn:
            conn.execute("CREATE TABLE test_table (id TEXT, name TEXT)")
            conn.commit()
            _ensure_unique_index(conn, "test_table", ["id"])
            # Check index was created
            indexes = conn.execute("PRAGMA index_list('test_table')").fetchall()
            index_names = [idx[1] for idx in indexes]
            assert "ux_test_table_id" in index_names

    def test_ensure_unique_index_skips_if_exists(self, mock_db):
        """Test that duplicate index creation is skipped."""
        with sqlite3.connect(str(mock_db)) as conn:
            conn.execute("CREATE TABLE test_table (id TEXT)")
            conn.execute("CREATE UNIQUE INDEX ux_test_table_id ON test_table (id)")
            conn.commit()
            # Should not raise error
            _ensure_unique_index(conn, "test_table", ["id"])

    def test_ensure_unique_index_handles_empty_columns(self, mock_db):
        """Test that empty column list is handled gracefully."""
        with sqlite3.connect(str(mock_db)) as conn:
            conn.execute("CREATE TABLE test_table (id TEXT)")
            conn.commit()
            _ensure_unique_index(conn, "test_table", [])
            # No error should be raised

    def test_ensure_unique_index_filters_nonexistent_columns(self, mock_db):
        """Test that columns not in table are filtered out."""
        with sqlite3.connect(str(mock_db)) as conn:
            conn.execute("CREATE TABLE test_table (id TEXT, name TEXT)")
            conn.commit()
            # Request index on columns, one of which doesn't exist
            _ensure_unique_index(conn, "test_table", ["id", "nonexistent"])
            # Should only create index on 'id'
            indexes = conn.execute("PRAGMA index_list('test_table')").fetchall()
            assert len(indexes) == 1


class TestEnsureTableExists:
    """Tests for ensure_table_exists function."""

    def test_ensure_table_exists_creates_table(self, mock_db, sample_schema):
        """Test that table is created with correct schema."""
        ensure_table_exists(mock_db, "test_table", sample_schema)
        with sqlite3.connect(str(mock_db)) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "test_table" in tables

    def test_ensure_table_exists_creates_columns(self, mock_db, sample_schema):
        """Test that all schema columns are created."""
        ensure_table_exists(mock_db, "test_table", sample_schema)
        with sqlite3.connect(str(mock_db)) as conn:
            cursor = conn.execute("PRAGMA table_info('test_table')")
            columns = [row[1] for row in cursor.fetchall()]
            for col_name in sample_schema["name"]:
                assert col_name in columns

    def test_ensure_table_exists_idempotent(self, mock_db, sample_schema):
        """Test that calling twice doesn't cause errors."""
        ensure_table_exists(mock_db, "test_table", sample_schema)
        # Should not raise error
        ensure_table_exists(mock_db, "test_table", sample_schema)

    def test_ensure_table_exists_creates_unique_index(self, mock_db, sample_schema):
        """Test that unique index is created on DETAILURL."""
        # Add DETAILURL to schema if not present
        schema_with_unique = sample_schema.copy()
        if "DETAILURL" not in schema_with_unique["name"].values:
            schema_with_unique = pd.concat(
                [schema_with_unique, pd.DataFrame({"name": ["DETAILURL"]})], ignore_index=True
            )
        ensure_table_exists(mock_db, "test_table", schema_with_unique)
        with sqlite3.connect(str(mock_db)) as conn:
            indexes = conn.execute("PRAGMA index_list('test_table')").fetchall()
            index_names = [idx[1] for idx in indexes]
            assert any("detailurl" in name.lower() for name in index_names)


class TestBuildKeySeries:
    """Tests for _build_key_series function."""

    def test_build_key_series_combines_columns(self):
        """Test that key columns are combined with joiner."""
        df = pd.DataFrame({"col1": ["a", "b"], "col2": ["x", "y"]})
        result = _build_key_series(df, ["col1", "col2"])
        assert result.tolist() == [f"a{KEY_JOINER}x", f"b{KEY_JOINER}y"]

    def test_build_key_series_handles_nan(self):
        """Test that NaN values are converted to empty strings."""
        df = pd.DataFrame({"col1": ["a", None], "col2": [None, "y"]})
        result = _build_key_series(df, ["col1", "col2"])
        assert result.tolist() == [f"a{KEY_JOINER}", f"{KEY_JOINER}y"]

    def test_build_key_series_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = _build_key_series(df, ["col1"])
        assert len(result) == 0

    def test_build_key_series_empty_columns(self):
        """Test with empty columns list."""
        df = pd.DataFrame({"col1": ["a", "b"]})
        result = _build_key_series(df, [])
        assert len(result) == 0

    def test_build_key_series_single_column(self):
        """Test with single key column."""
        df = pd.DataFrame({"id": [1, 2, 3]})
        result = _build_key_series(df, ["id"])
        assert result.tolist() == ["1", "2", "3"]


class TestPersistToSQLite:
    """Tests for persist_to_sqlite function."""

    def test_persist_to_sqlite_inserts_new_records(self, mock_db, sample_dataframe, sample_schema):
        """Test that new records are inserted into database."""
        ensure_table_exists(mock_db, "test_table", sample_schema)
        persist_to_sqlite(sample_dataframe, mock_db, "test_table")
        with sqlite3.connect(str(mock_db)) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test_table")
            count = cursor.fetchone()[0]
            assert count == len(sample_dataframe)

    def test_persist_to_sqlite_handles_empty_dataframe(self, mock_db, sample_schema):
        """Test that empty DataFrame is handled gracefully."""
        ensure_table_exists(mock_db, "test_table", sample_schema)
        empty_df = pd.DataFrame(columns=sample_schema["name"])
        persist_to_sqlite(empty_df, mock_db, "test_table")
        with sqlite3.connect(str(mock_db)) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test_table")
            count = cursor.fetchone()[0]
            assert count == 0

    def test_persist_to_sqlite_deduplicates_by_key(self, mock_db, sample_schema):
        """Test that duplicate records (by DETAILURL) are not inserted."""
        schema_with_detail = sample_schema.copy()
        if "DETAILURL" not in schema_with_detail["name"].values:
            schema_with_detail = pd.concat(
                [schema_with_detail, pd.DataFrame({"name": ["DETAILURL"]})], ignore_index=True
            )
        ensure_table_exists(mock_db, "test_table", schema_with_detail)

        df1 = pd.DataFrame(
            {
                "DETAILURL": ["http://test1", "http://test2"],
                "PRICE": [2000, 1800],
            }
        )
        persist_to_sqlite(df1, mock_db, "test_table")

        # Try to insert duplicate
        df2 = pd.DataFrame({"DETAILURL": ["http://test1"], "PRICE": [2200]})
        persist_to_sqlite(df2, mock_db, "test_table")

        with sqlite3.connect(str(mock_db)) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test_table")
            count = cursor.fetchone()[0]
            # Should still be 2, not 3
            assert count == 2

    def test_persist_to_sqlite_updates_ingestion_date(self, mock_db, sample_schema):
        """Test that ingestion date is updated for existing records."""
        schema_with_fields = sample_schema.copy()
        extra_cols = pd.DataFrame({"name": ["DETAILURL", "INGESTION_DATE"]})
        schema_with_fields = pd.concat(
            [schema_with_fields, extra_cols], ignore_index=True
        ).drop_duplicates(subset="name")

        ensure_table_exists(mock_db, "test_table", schema_with_fields)

        # Insert initial record
        df1 = pd.DataFrame(
            {"DETAILURL": ["http://test1"], "PRICE": [2000], "INGESTION_DATE": ["20251020"]}
        )
        persist_to_sqlite(df1, mock_db, "test_table")

        # Update with new ingestion date
        df2 = pd.DataFrame(
            {"DETAILURL": ["http://test1"], "PRICE": [2000], "INGESTION_DATE": ["20251027"]}
        )
        persist_to_sqlite(df2, mock_db, "test_table")

        with sqlite3.connect(str(mock_db)) as conn:
            cursor = conn.execute(
                'SELECT INGESTION_DATE FROM test_table WHERE DETAILURL = "http://test1"'
            )
            ingestion_date = cursor.fetchone()[0]
            assert ingestion_date == "20251027"

    def test_persist_to_sqlite_fills_missing_table_columns(self, mock_db, sample_schema):
        """Test that missing columns are filled with empty strings."""
        ensure_table_exists(mock_db, "test_table", sample_schema)
        # Insert DataFrame with only some columns
        partial_df = pd.DataFrame({"PRICE": [2000]})
        persist_to_sqlite(partial_df, mock_db, "test_table")

        with sqlite3.connect(str(mock_db)) as conn:
            cursor = conn.execute("SELECT * FROM test_table")
            row = cursor.fetchone()
            # Should have values for all schema columns
            assert len(row) == len(sample_schema)

    def test_persist_to_sqlite_removes_duplicates_in_input(self, mock_db, sample_schema):
        """Test that input DataFrame is deduplicated before insertion."""
        schema_with_detail = sample_schema.copy()
        if "DETAILURL" not in schema_with_detail["name"].values:
            schema_with_detail = pd.concat(
                [schema_with_detail, pd.DataFrame({"name": ["DETAILURL"]})], ignore_index=True
            )
        ensure_table_exists(mock_db, "test_table", schema_with_detail)

        # DataFrame with duplicate DETAILURL
        df = pd.DataFrame(
            {
                "DETAILURL": ["http://test1", "http://test1", "http://test2"],
                "PRICE": [2000, 2100, 1800],
            }
        )
        persist_to_sqlite(df, mock_db, "test_table")

        with sqlite3.connect(str(mock_db)) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test_table")
            count = cursor.fetchone()[0]
            # Should only insert 2 records (duplicates removed)
            assert count == 2
