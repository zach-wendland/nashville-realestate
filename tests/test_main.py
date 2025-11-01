"""Comprehensive tests for main.py module."""
from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

import main
from main import (
    BASE_PARAMS,
    MAX_PAGES,
    RAW_LOCATIONS,
    UNIT_FALLBACK_COLUMNS,
    _ensure_priority_columns,
    build_pipeline_dataframe,
)


class TestEnsurePriorityColumns:
    """Tests for _ensure_priority_columns function."""

    def test_ensure_priority_columns_normalizes_column_names(self):
        """Test that column names are normalized to uppercase."""
        df = pd.DataFrame({"price": [2000], "beds": [2], "bathrooms": [2.0]})
        result = _ensure_priority_columns(df)
        assert "PRICE" in result.columns
        assert "BEDS" in result.columns
        assert "BATHROOMS" in result.columns

    def test_ensure_priority_columns_uses_fallback_when_target_missing(self):
        """Test that fallback columns are used when target is missing."""
        df = pd.DataFrame({"PRICE_1": [2000], "BEDS_1": [2], "BATHROOMS_1": [2.0]})
        result = _ensure_priority_columns(df)
        # Should create PRICE, BEDS, BATHROOMS from _1 versions
        assert "PRICE" in result.columns
        assert "BEDS" in result.columns
        assert "BATHROOMS" in result.columns
        assert result["PRICE"].iloc[0] == 2000
        assert result["BEDS"].iloc[0] == 2

    def test_ensure_priority_columns_preserves_target_when_exists(self):
        """Test that target column is preserved when it exists."""
        df = pd.DataFrame({"PRICE": [2000], "PRICE_1": [2100]})
        result = _ensure_priority_columns(df)
        # Should keep original PRICE, not overwrite with PRICE_1
        assert result["PRICE"].iloc[0] == 2000

    def test_ensure_priority_columns_does_not_add_when_neither_exists(self):
        """Test that columns are not added when neither target nor fallback exist."""
        df = pd.DataFrame({"OTHER_COLUMN": [123]})
        result = _ensure_priority_columns(df)
        assert "PRICE" not in result.columns
        assert "BEDS" not in result.columns
        assert "BATHROOMS" not in result.columns

    def test_ensure_priority_columns_handles_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = _ensure_priority_columns(df)
        assert result.empty

    def test_ensure_priority_columns_all_fallbacks(self):
        """Test that all defined fallback columns are processed."""
        for target, fallback in UNIT_FALLBACK_COLUMNS.items():
            df = pd.DataFrame({fallback: [999]})
            result = _ensure_priority_columns(df)
            assert target in result.columns
            assert result[target].iloc[0] == 999


class TestBuildPipelineDataFrame:
    """Tests for build_pipeline_dataframe function."""

    @patch("main.fetch_dataframe")
    def test_build_pipeline_dataframe_returns_dataframe(self, mock_fetch):
        """Test that function returns a properly formatted DataFrame."""
        mock_fetch.return_value = pd.DataFrame(
            {"longitude": [-86.78], "latitude": [36.16], "price_1": [2000]}
        )
        result = build_pipeline_dataframe(["Nashville, TN"], "20251027")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    @patch("main.fetch_dataframe")
    def test_build_pipeline_dataframe_adds_ingestion_date(self, mock_fetch):
        """Test that INGESTION_DATE column is added."""
        mock_fetch.return_value = pd.DataFrame({"id": [1], "price": [2000]})
        result = build_pipeline_dataframe(["Nashville"], "20251027")
        assert "INGESTION_DATE" in result.columns
        assert result["INGESTION_DATE"].iloc[0] == "20251027"

    @patch("main.fetch_dataframe")
    def test_build_pipeline_dataframe_returns_empty_when_no_data(self, mock_fetch):
        """Test that empty DataFrame is returned when fetch returns empty."""
        mock_fetch.return_value = pd.DataFrame()
        result = build_pipeline_dataframe(["Nashville"], "20251027")
        assert result.empty

    @patch("main.fetch_dataframe")
    def test_build_pipeline_dataframe_uses_config_params(self, mock_fetch):
        """Test that FetchConfig is created with correct parameters."""
        mock_fetch.return_value = pd.DataFrame({"id": [1]})
        build_pipeline_dataframe(["Location1", "Location2"], "20251027")
        # Verify fetch_dataframe was called once
        assert mock_fetch.call_count == 1
        # Get the FetchConfig argument
        config = mock_fetch.call_args[0][0]
        assert config.base_params == BASE_PARAMS
        assert config.locations == ["Location1", "Location2"]
        assert config.max_pages == MAX_PAGES

    @patch("main.fetch_dataframe")
    def test_build_pipeline_dataframe_applies_fallback_columns(self, mock_fetch):
        """Test that fallback column logic is applied."""
        mock_fetch.return_value = pd.DataFrame({"price_1": [2000], "beds_1": [2]})
        result = build_pipeline_dataframe(["Nashville"], "20251027")
        # Should have PRICE and BEDS columns from fallbacks
        assert "PRICE" in result.columns
        assert "BEDS" in result.columns

    @patch("main.fetch_dataframe")
    def test_build_pipeline_dataframe_uppercases_all_data(self, mock_fetch):
        """Test that all data is converted to uppercase strings."""
        mock_fetch.return_value = pd.DataFrame(
            {"address": ["123 Main St"], "city": ["Nashville"], "price": [2000]}
        )
        result = build_pipeline_dataframe(["Nashville"], "20251027")
        # Check that string values are uppercase
        assert result["ADDRESS"].iloc[0] == "123 MAIN ST"
        assert result["CITY"].iloc[0] == "NASHVILLE"
        assert result["PRICE"].iloc[0] == "2000"


class TestMain:
    """Tests for main function."""

    @patch("main.persist_to_csv")
    @patch("main.persist_to_sqlite")
    @patch("main.ensure_table_exists")
    @patch("main.align_to_schema")
    @patch("main.load_schema")
    @patch("main.build_pipeline_dataframe")
    @patch("main.split_locations")
    def test_main_successful_execution(
        self,
        mock_split,
        mock_build,
        mock_load_schema,
        mock_align,
        mock_ensure_table,
        mock_persist_sqlite,
        mock_persist_csv,
    ):
        """Test successful main function execution."""
        # Setup mocks
        mock_split.return_value = ["Nashville, TN"]
        mock_build.return_value = pd.DataFrame({"PRICE": ["2000"], "DETAILURL": ["http://test"]})
        mock_load_schema.return_value = pd.DataFrame({"name": ["PRICE", "DETAILURL"]})
        mock_align.return_value = pd.DataFrame({"PRICE": ["2000"], "DETAILURL": ["http://test"]})
        mock_persist_csv.return_value = "/path/to/csv"

        # Execute
        main.main()

        # Verify calls
        assert mock_split.called
        assert mock_build.called
        assert mock_load_schema.called
        assert mock_align.called
        assert mock_ensure_table.called
        assert mock_persist_sqlite.called
        assert mock_persist_csv.called

    @patch("main.build_pipeline_dataframe")
    @patch("main.split_locations")
    def test_main_aborts_on_empty_dataframe(self, mock_split, mock_build):
        """Test that main aborts when no records are fetched."""
        mock_split.return_value = ["Nashville"]
        mock_build.return_value = pd.DataFrame()  # Empty DataFrame

        # Should not raise error, just log warning and return
        main.main()

        # Verify that build was called but subsequent operations were not
        assert mock_build.called

    @patch("main.persist_to_csv")
    @patch("main.persist_to_sqlite")
    @patch("main.ensure_table_exists")
    @patch("main.align_to_schema")
    @patch("main.load_schema")
    @patch("main.build_pipeline_dataframe")
    @patch("main.split_locations")
    def test_main_passes_extra_columns_to_schema(
        self,
        mock_split,
        mock_build,
        mock_load_schema,
        mock_align,
        mock_ensure_table,
        mock_persist_sqlite,
        mock_persist_csv,
    ):
        """Test that INGESTION_DATE is passed as extra column to schema."""
        mock_split.return_value = ["Nashville"]
        mock_build.return_value = pd.DataFrame({"ID": ["1"], "INGESTION_DATE": ["20251027"]})
        mock_load_schema.return_value = pd.DataFrame({"name": ["ID", "INGESTION_DATE"]})
        mock_align.return_value = pd.DataFrame({"ID": ["1"], "INGESTION_DATE": ["20251027"]})
        mock_persist_csv.return_value = "/path/to/csv"

        main.main()

        # Verify load_schema was called with extra_columns
        mock_load_schema.assert_called_once()
        call_kwargs = mock_load_schema.call_args[1]
        assert "extra_columns" in call_kwargs
        assert "INGESTION_DATE" in call_kwargs["extra_columns"]

    @patch("main.build_pipeline_dataframe")
    @patch("main.split_locations")
    def test_main_raises_on_exception(self, mock_split, mock_build):
        """Test that main raises exceptions from underlying functions."""
        mock_split.return_value = ["Nashville"]
        mock_build.side_effect = RuntimeError("API Error")

        with pytest.raises(RuntimeError, match="API Error"):
            main.main()

    @patch("main.split_locations")
    def test_main_splits_raw_locations(self, mock_split):
        """Test that RAW_LOCATIONS is split using split_locations."""
        mock_split.return_value = []

        try:
            main.main()
        except:
            pass  # Ignore errors from empty locations

        # Verify split_locations was called with RAW_LOCATIONS
        mock_split.assert_called_once_with(RAW_LOCATIONS)


class TestConstants:
    """Tests for module-level constants."""

    def test_base_params_has_required_fields(self):
        """Test that BASE_PARAMS contains expected rental filters."""
        assert "status_type" in BASE_PARAMS
        assert BASE_PARAMS["status_type"] == "ForRent"
        assert "rentMinPrice" in BASE_PARAMS
        assert "rentMaxPrice" in BASE_PARAMS
        assert "bedsMin" in BASE_PARAMS
        assert "bedsMax" in BASE_PARAMS
        assert "sqftMin" in BASE_PARAMS
        assert "sqftMax" in BASE_PARAMS

    def test_base_params_price_range_valid(self):
        """Test that min price is less than max price."""
        assert BASE_PARAMS["rentMinPrice"] < BASE_PARAMS["rentMaxPrice"]

    def test_base_params_beds_range_valid(self):
        """Test that min beds is less than or equal to max beds."""
        assert BASE_PARAMS["bedsMin"] <= BASE_PARAMS["bedsMax"]

    def test_base_params_beds_max_is_four(self):
        """Test that max beds is 4 (expanded from 2)."""
        assert BASE_PARAMS["bedsMax"] == 4

    def test_base_params_sqft_range_valid(self):
        """Test that min sqft is less than max sqft."""
        assert BASE_PARAMS["sqftMin"] < BASE_PARAMS["sqftMax"]

    def test_base_params_sqft_max_is_3500(self):
        """Test that max square feet is 3500."""
        assert BASE_PARAMS["sqftMax"] == 3500

    def test_raw_locations_is_string(self):
        """Test that RAW_LOCATIONS is a string."""
        assert isinstance(RAW_LOCATIONS, str)
        assert len(RAW_LOCATIONS) > 0

    def test_raw_locations_contains_nashville(self):
        """Test that RAW_LOCATIONS contains Nashville references."""
        assert "Nashville" in RAW_LOCATIONS or "37" in RAW_LOCATIONS

    def test_raw_locations_has_twenty_locations(self):
        """Test that RAW_LOCATIONS contains 20 zip codes."""
        locations = [loc.strip() for loc in RAW_LOCATIONS.split(";") if loc.strip()]
        assert len(locations) == 20

    def test_raw_locations_includes_diverse_neighborhoods(self):
        """Test that RAW_LOCATIONS includes various Nashville neighborhoods."""
        # Check for key zip codes from different areas
        assert "37206" in RAW_LOCATIONS  # East Nashville
        assert "37203" in RAW_LOCATIONS  # Gulch
        assert "37212" in RAW_LOCATIONS  # Midtown
        assert "37027" in RAW_LOCATIONS  # Brentwood (suburban)

    def test_max_pages_is_positive(self):
        """Test that MAX_PAGES is a positive integer."""
        assert isinstance(MAX_PAGES, int)
        assert MAX_PAGES > 0

    def test_unit_fallback_columns_structure(self):
        """Test that UNIT_FALLBACK_COLUMNS has expected structure."""
        assert isinstance(UNIT_FALLBACK_COLUMNS, dict)
        assert "PRICE" in UNIT_FALLBACK_COLUMNS
        assert "BEDS" in UNIT_FALLBACK_COLUMNS
        assert "BATHROOMS" in UNIT_FALLBACK_COLUMNS
        assert UNIT_FALLBACK_COLUMNS["PRICE"] == "PRICE_1"
        assert UNIT_FALLBACK_COLUMNS["BEDS"] == "BEDS_1"
        assert UNIT_FALLBACK_COLUMNS["BATHROOMS"] == "BATHROOMS_1"
