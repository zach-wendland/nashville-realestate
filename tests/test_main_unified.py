"""Tests for unified pipeline orchestration."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from db.db_config import FORSALE_CONFIG, PRIMARY_KEY_COLUMN, RENT_CONFIG
from main_unified import (
    FORSALE_PARAMS,
    RENT_PARAMS,
    build_pipeline_dataframe,
    process_location_batch,
    run_all_pipelines,
    run_forsale_pipeline,
    run_pipeline,
    run_rent_pipeline,
)


class TestRunPipeline:
    """Tests for run_pipeline function with config-driven execution."""

    @patch("main_unified.fetch_dataframe")
    @patch("main_unified.persist_to_sqlite")
    @patch("main_unified.persist_to_csv")
    @patch("main_unified.ensure_table_exists")
    def test_run_rent_pipeline_uses_rent_config(
        self, mock_ensure, mock_csv, mock_sqlite, mock_fetch, sample_rent_data
    ):
        """Rental pipeline should use RENT_CONFIG."""
        mock_fetch.return_value = sample_rent_data

        run_rent_pipeline()

        # Verify correct config passed to persist functions
        assert mock_sqlite.call_count == 1
        call_args = mock_sqlite.call_args
        assert call_args[0][1] == RENT_CONFIG  # Second arg is config

    @patch("main_unified.fetch_dataframe")
    @patch("main_unified.persist_to_sqlite")
    @patch("main_unified.persist_to_csv")
    @patch("main_unified.ensure_table_exists")
    def test_run_forsale_pipeline_uses_forsale_config(
        self, mock_ensure, mock_csv, mock_sqlite, mock_fetch, sample_forsale_data
    ):
        """For-sale pipeline should use FORSALE_CONFIG."""
        mock_fetch.return_value = sample_forsale_data

        run_forsale_pipeline()

        # Verify correct config passed
        assert mock_sqlite.call_count == 1
        call_args = mock_sqlite.call_args
        assert call_args[0][1] == FORSALE_CONFIG

    @patch("main_unified.run_forsale_pipeline")
    @patch("main_unified.run_rent_pipeline")
    def test_run_all_pipelines_executes_both_sequentially(self, mock_rent, mock_forsale):
        """run_all_pipelines should execute both pipelines."""
        run_all_pipelines()

        assert mock_rent.call_count == 1
        assert mock_forsale.call_count == 1

    @patch("main_unified.split_locations")
    @patch("main_unified.process_location_batch")
    @patch("main_unified.persist_to_sqlite")
    @patch("main_unified.persist_to_csv")
    @patch("main_unified.ensure_table_exists")
    def test_run_pipeline_batch_processing(
        self, mock_ensure, mock_csv, mock_sqlite, mock_batch, mock_split, sample_rent_data
    ):
        """Pipeline should process locations in batches."""
        # Mock 10 locations split into batches of 5
        mock_split.return_value = [f"Location{i}" for i in range(10)]
        mock_batch.return_value = sample_rent_data

        run_pipeline(RENT_CONFIG, RENT_PARAMS, batch_size=5)

        # Should call process_location_batch twice (10 locations / 5 per batch)
        assert mock_batch.call_count == 2

    @patch("main_unified.split_locations")
    @patch("main_unified.process_location_batch")
    def test_run_pipeline_handles_empty_results(self, mock_batch, mock_split):
        """Pipeline should handle empty results gracefully."""
        mock_split.return_value = ["Location1"]
        mock_batch.return_value = None  # No data returned

        # Should not raise exception
        run_pipeline(RENT_CONFIG, RENT_PARAMS)

    @patch("main_unified.split_locations")
    @patch("main_unified.process_location_batch")
    @patch("main_unified.persist_to_sqlite")
    @patch("main_unified.persist_to_csv")
    @patch("main_unified.ensure_table_exists")
    def test_run_pipeline_partial_batch_failure_continues(
        self, mock_ensure, mock_csv, mock_sqlite, mock_batch, mock_split, sample_rent_data
    ):
        """Pipeline should continue if one batch fails but another succeeds."""
        mock_split.return_value = ["Loc1", "Loc2"]

        # First batch fails, second succeeds
        mock_batch.side_effect = [None, sample_rent_data]

        run_pipeline(RENT_CONFIG, RENT_PARAMS, batch_size=1)

        # Should still persist the successful batch
        assert mock_sqlite.call_count == 1


class TestBuildPipelineDataframe:
    """Tests for build_pipeline_dataframe function."""

    @patch("main_unified.fetch_dataframe")
    def test_assigns_primary_keys(self, mock_fetch, sample_rent_data):
        """build_pipeline_dataframe should assign primary keys."""
        # Remove any existing keys from sample data
        if PRIMARY_KEY_COLUMN in sample_rent_data.columns:
            sample_rent_data = sample_rent_data.drop(columns=[PRIMARY_KEY_COLUMN])

        mock_fetch.return_value = sample_rent_data

        result = build_pipeline_dataframe(
            ["Nashville, TN"],
            "20251110",
            RENT_PARAMS,
            RENT_CONFIG
        )

        assert PRIMARY_KEY_COLUMN in result.columns
        assert result[PRIMARY_KEY_COLUMN].notna().all()

    @patch("main_unified.fetch_dataframe")
    def test_adds_ingestion_date(self, mock_fetch, sample_rent_data):
        """build_pipeline_dataframe should add INGESTION_DATE column."""
        mock_fetch.return_value = sample_rent_data

        result = build_pipeline_dataframe(
            ["Nashville, TN"],
            "20251110",
            RENT_PARAMS,
            RENT_CONFIG
        )

        assert "INGESTION_DATE" in result.columns
        assert all(result["INGESTION_DATE"] == "20251110")

    @patch("main_unified.fetch_dataframe")
    def test_handles_empty_response(self, mock_fetch):
        """build_pipeline_dataframe should handle empty API response."""
        mock_fetch.return_value = pd.DataFrame()

        result = build_pipeline_dataframe(
            ["Nashville, TN"],
            "20251110",
            RENT_PARAMS,
            RENT_CONFIG
        )

        assert result.empty


class TestProcessLocationBatch:
    """Tests for process_location_batch function."""

    @patch("main_unified.build_pipeline_dataframe")
    def test_returns_none_on_empty_dataframe(self, mock_build):
        """process_location_batch should return None when DataFrame is empty."""
        mock_build.return_value = pd.DataFrame()

        result = process_location_batch(
            ["Nashville, TN"],
            "20251110",
            RENT_PARAMS,
            RENT_CONFIG
        )

        assert result is None

    @patch("main_unified.build_pipeline_dataframe")
    def test_returns_dataframe_on_success(self, mock_build, sample_rent_data):
        """process_location_batch should return DataFrame on success."""
        mock_build.return_value = sample_rent_data

        result = process_location_batch(
            ["Nashville, TN"],
            "20251110",
            RENT_PARAMS,
            RENT_CONFIG
        )

        assert isinstance(result, pd.DataFrame)
        assert not result.empty


class TestPipelineParameters:
    """Tests for pipeline parameter configuration."""

    def test_rent_params_use_forrent_status(self):
        """Rental parameters should use 'ForRent' status_type."""
        assert RENT_PARAMS["status_type"] == "ForRent"
        assert "rentMinPrice" in RENT_PARAMS
        assert "rentMaxPrice" in RENT_PARAMS

    def test_forsale_params_use_forsale_status(self):
        """For-sale parameters should use 'ForSale' status_type."""
        assert FORSALE_PARAMS["status_type"] == "ForSale"
        assert "minPrice" in FORSALE_PARAMS
        assert "maxPrice" in FORSALE_PARAMS

    def test_params_have_different_price_keys(self):
        """Rent and for-sale params should use different price parameter names."""
        rent_keys = set(RENT_PARAMS.keys())
        forsale_keys = set(FORSALE_PARAMS.keys())

        # Rent uses rentMinPrice/rentMaxPrice
        assert "rentMinPrice" in rent_keys
        assert "rentMaxPrice" in rent_keys

        # ForSale uses minPrice/maxPrice
        assert "minPrice" in forsale_keys
        assert "maxPrice" in forsale_keys
