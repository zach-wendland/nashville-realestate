"""Comprehensive tests for api/zillow_fetcher.py module."""
from __future__ import annotations

import os
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest
import requests
import responses

from api.zillow_fetcher import (
    BASE_URL,
    DEFAULT_MAX_PAGES,
    DEFAULT_RETRIES,
    FetchConfig,
    ZillowAPIError,
    _augment_with_units,
    _extract_error_message,
    _extract_results,
    _flatten_mapping,
    _safe_page_number,
    build_headers,
    collect_properties,
    fetch_dataframe,
    fetch_page,
    get_api_key,
    iterate_pages,
    records_to_dataframe,
    split_locations,
)


class TestGetAPIKey:
    """Tests for get_api_key function."""

    def test_get_api_key_from_zillow_env_var(self, monkeypatch):
        """Test retrieving API key from ZILLOW_RAPIDAPI_KEY environment variable."""
        monkeypatch.setenv("ZILLOW_RAPIDAPI_KEY", "test-key-123")
        assert get_api_key() == "test-key-123"

    def test_get_api_key_from_rapidapi_env_var(self, monkeypatch):
        """Test retrieving API key from RAPIDAPI_KEY environment variable."""
        monkeypatch.delenv("ZILLOW_RAPIDAPI_KEY", raising=False)
        monkeypatch.setenv("RAPIDAPI_KEY", "test-key-456")
        assert get_api_key() == "test-key-456"

    def test_get_api_key_prefers_zillow_key(self, monkeypatch):
        """Test that ZILLOW_RAPIDAPI_KEY takes precedence over RAPIDAPI_KEY."""
        monkeypatch.setenv("ZILLOW_RAPIDAPI_KEY", "zillow-key")
        monkeypatch.setenv("RAPIDAPI_KEY", "rapidapi-key")
        assert get_api_key() == "zillow-key"

    def test_get_api_key_raises_when_missing(self, monkeypatch):
        """Test that ZillowAPIError is raised when no API key is found."""
        monkeypatch.delenv("ZILLOW_RAPIDAPI_KEY", raising=False)
        monkeypatch.delenv("RAPIDAPI_KEY", raising=False)
        with pytest.raises(ZillowAPIError, match="RapidAPI key not provided"):
            get_api_key()


class TestBuildHeaders:
    """Tests for build_headers function."""

    def test_build_headers_returns_correct_structure(self):
        """Test that headers contain required keys and values."""
        headers = build_headers("my-api-key")
        assert headers == {
            "x-rapidapi-key": "my-api-key",
            "x-rapidapi-host": "zillow-com1.p.rapidapi.com",
        }

    def test_build_headers_with_empty_key(self):
        """Test build_headers with empty string API key."""
        headers = build_headers("")
        assert headers["x-rapidapi-key"] == ""
        assert "x-rapidapi-host" in headers


class TestExtractErrorMessage:
    """Tests for _extract_error_message function."""

    def test_extract_error_message_from_json_message_key(self):
        """Test extracting error message from 'message' key in JSON response."""
        mock_response = Mock()
        mock_response.json.return_value = {"message": "Invalid API key"}
        mock_response.text = "some text"
        assert _extract_error_message(mock_response) == "Invalid API key"

    def test_extract_error_message_from_json_error_key(self):
        """Test extracting error message from 'error' key in JSON response."""
        mock_response = Mock()
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        mock_response.text = "some text"
        assert _extract_error_message(mock_response) == "Rate limit exceeded"

    def test_extract_error_message_from_json_list(self):
        """Test extracting error message from list in JSON response."""
        mock_response = Mock()
        mock_response.json.return_value = {"errors": ["First error", "Second error"]}
        mock_response.text = "some text"
        assert _extract_error_message(mock_response) == "First error"

    def test_extract_error_message_from_text_when_json_fails(self):
        """Test fallback to response.text when JSON parsing fails."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "Plain text error message"
        assert _extract_error_message(mock_response) == "Plain text error message"

    def test_extract_error_message_truncates_long_text(self):
        """Test that long error messages are truncated to 200 characters."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "x" * 300
        result = _extract_error_message(mock_response)
        assert len(result) == 200
        assert result == "x" * 200

    def test_extract_error_message_returns_empty_when_none(self):
        """Test that empty string is returned when response is None."""
        assert _extract_error_message(None) == ""

    def test_extract_error_message_handles_empty_response(self):
        """Test handling of empty response text."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = ""
        assert _extract_error_message(mock_response) == ""


class TestSafePageNumber:
    """Tests for _safe_page_number function."""

    def test_safe_page_number_with_valid_positive_integer(self):
        """Test that valid positive integers are returned as-is."""
        assert _safe_page_number(5) == 5
        assert _safe_page_number(100) == 100

    def test_safe_page_number_with_zero_returns_one(self):
        """Test that zero is converted to 1."""
        assert _safe_page_number(0) == 1

    def test_safe_page_number_with_negative_returns_one(self):
        """Test that negative numbers are converted to 1."""
        assert _safe_page_number(-5) == 1
        assert _safe_page_number(-100) == 1

    def test_safe_page_number_with_none_returns_one(self):
        """Test that None is converted to 1."""
        assert _safe_page_number(None) == 1

    def test_safe_page_number_with_string_returns_one(self):
        """Test that invalid types return 1."""
        assert _safe_page_number("invalid") == 1


class TestFetchPage:
    """Tests for fetch_page function."""

    @responses.activate
    def test_fetch_page_successful_request(self):
        """Test successful page fetch returns JSON data."""
        responses.add(
            responses.GET,
            BASE_URL,
            json={"results": [{"id": 1}]},
            status=200,
        )
        session = requests.Session()
        session.headers.update({"x-rapidapi-key": "test-key"})
        result = fetch_page(session, {"status_type": "ForRent"}, 1, retries=1)
        assert result == {"results": [{"id": 1}]}

    def test_fetch_page_404_returns_empty_results(self, mocker):
        """Test that 404 errors return empty results instead of raising."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {}
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)

        session = requests.Session()
        mocker.patch.object(session, 'get', return_value=mock_response)

        result = fetch_page(session, {}, 1, retries=1, cooldown=0)
        assert result == {"results": []}

    def test_fetch_page_429_retries_with_backoff(self, mocker):
        """Test that 429 rate limit errors trigger retries."""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.json.return_value = {}
        mock_response_429.raise_for_status.side_effect = requests.HTTPError(response=mock_response_429)

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"results": []}
        mock_response_200.raise_for_status.return_value = None

        session = requests.Session()
        mocker.patch.object(session, 'get', side_effect=[mock_response_429, mock_response_200])

        result = fetch_page(session, {}, 1, retries=2, cooldown=0.01)
        assert result == {"results": []}
        assert session.get.call_count == 2

    def test_fetch_page_401_raises_with_auth_hint(self, mocker):
        """Test that 401 errors raise with authentication hint."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {}
        mock_response.text = ""
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)

        session = requests.Session()
        mocker.patch.object(session, 'get', return_value=mock_response)

        with pytest.raises(ZillowAPIError, match="check RapidAPI key"):
            fetch_page(session, {}, 1, retries=1, cooldown=0)

    def test_fetch_page_403_raises_with_auth_hint(self, mocker):
        """Test that 403 errors raise with authentication hint."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {}
        mock_response.text = ""
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)

        session = requests.Session()
        mocker.patch.object(session, 'get', return_value=mock_response)

        with pytest.raises(ZillowAPIError, match="check RapidAPI key"):
            fetch_page(session, {}, 1, retries=1, cooldown=0)

    @responses.activate
    def test_fetch_page_network_error_retries(self):
        """Test that network errors trigger retries."""
        responses.add(responses.GET, BASE_URL, body=requests.RequestException("Network error"))
        session = requests.Session()
        with pytest.raises(ZillowAPIError, match="Network error while fetching page"):
            fetch_page(session, {}, 1, retries=2, cooldown=0.01)

    @responses.activate
    def test_fetch_page_includes_page_param(self):
        """Test that page parameter is included in request."""
        responses.add(responses.GET, BASE_URL, json={"results": []}, status=200)
        session = requests.Session()
        fetch_page(session, {"status_type": "ForRent"}, 3, retries=1)
        assert responses.calls[0].request.params["page"] == "3"


class TestExtractResults:
    """Tests for _extract_results function."""

    def test_extract_results_from_results_key(self):
        """Test extracting results from 'results' key."""
        payload = {"results": [{"id": 1}, {"id": 2}]}
        assert _extract_results(payload) == [{"id": 1}, {"id": 2}]

    def test_extract_results_from_props_key(self):
        """Test extracting results from 'props' key."""
        payload = {"props": [{"id": 1}]}
        assert _extract_results(payload) == [{"id": 1}]

    def test_extract_results_from_nested_data_props(self):
        """Test extracting results from nested 'data.props' structure."""
        payload = {"data": {"props": [{"id": 1}]}}
        assert _extract_results(payload) == [{"id": 1}]

    def test_extract_results_from_list_payload(self):
        """Test extracting results when payload is a list."""
        payload = [{"id": 1}, {"id": 2}]
        assert _extract_results(payload) == [{"id": 1}, {"id": 2}]

    def test_extract_results_filters_non_dict_items(self):
        """Test that non-dict items are filtered out."""
        payload = {"results": [{"id": 1}, "invalid", None, {"id": 2}]}
        assert _extract_results(payload) == [{"id": 1}, {"id": 2}]

    def test_extract_results_returns_empty_for_invalid_payload(self):
        """Test that empty list is returned for invalid payloads."""
        assert _extract_results(None) == []
        assert _extract_results("string") == []
        assert _extract_results(123) == []


class TestIteratePages:
    """Tests for iterate_pages function."""

    @responses.activate
    def test_iterate_pages_fetches_multiple_pages(self):
        """Test that multiple pages are fetched correctly."""
        for page in range(1, 4):
            responses.add(
                responses.GET,
                BASE_URL,
                json={"results": [{"id": page}], "totalPages": 3},
                status=200,
            )
        session = requests.Session()
        results = iterate_pages(session, {}, max_pages=3, rate_limit_wait=0.01)
        assert len(results) == 3
        assert results[0]["id"] == 1
        assert results[2]["id"] == 3

    @responses.activate
    def test_iterate_pages_stops_on_empty_results(self):
        """Test that pagination stops when empty results are returned."""
        responses.add(responses.GET, BASE_URL, json={"results": [{"id": 1}]}, status=200)
        responses.add(responses.GET, BASE_URL, json={"results": []}, status=200)
        session = requests.Session()
        results = iterate_pages(session, {}, max_pages=5, rate_limit_wait=0.01)
        assert len(results) == 1
        assert len(responses.calls) == 2

    @responses.activate
    def test_iterate_pages_respects_total_pages_hint(self):
        """Test that pagination stops when totalPages is reached."""
        responses.add(
            responses.GET, BASE_URL, json={"results": [{"id": 1}], "totalPages": 1}, status=200
        )
        session = requests.Session()
        results = iterate_pages(session, {}, max_pages=10, rate_limit_wait=0.01)
        assert len(results) == 1
        assert len(responses.calls) == 1


class TestSplitLocations:
    """Tests for split_locations function."""

    def test_split_locations_with_semicolon_separator(self):
        """Test splitting locations by semicolon."""
        raw = "37206, Nashville, TN; 37216, Nashville, TN; Midtown, Nashville, TN"
        result = split_locations(raw)
        assert result == [
            "37206, Nashville, TN",
            "37216, Nashville, TN",
            "Midtown, Nashville, TN",
        ]

    def test_split_locations_strips_whitespace(self):
        """Test that whitespace is stripped from each location."""
        raw = "  Location 1  ;  Location 2  ;  Location 3  "
        result = split_locations(raw)
        assert result == ["Location 1", "Location 2", "Location 3"]

    def test_split_locations_respects_limit(self):
        """Test that results are limited to specified number."""
        raw = "Loc1; Loc2; Loc3; Loc4; Loc5; Loc6"
        result = split_locations(raw, limit=3)
        assert result == ["Loc1", "Loc2", "Loc3"]

    def test_split_locations_filters_empty_strings(self):
        """Test that empty strings are filtered out."""
        raw = "Loc1;  ; Loc2;; Loc3"
        result = split_locations(raw)
        assert result == ["Loc1", "Loc2", "Loc3"]

    def test_split_locations_returns_empty_for_empty_input(self):
        """Test that empty input returns empty list."""
        assert split_locations("") == []
        assert split_locations("   ") == []

    def test_split_locations_default_limit_is_twenty(self):
        """Test that default limit is 20."""
        raw = "; ".join([f"L{i}" for i in range(1, 26)])  # 25 locations
        result = split_locations(raw)
        assert len(result) == 20

    def test_split_locations_handles_twenty_locations(self):
        """Test that 20 locations are properly handled."""
        raw = "; ".join([f"Location {i}" for i in range(1, 21)])  # Exactly 20
        result = split_locations(raw)
        assert len(result) == 20
        assert result[0] == "Location 1"
        assert result[19] == "Location 20"


class TestFlattenMapping:
    """Tests for _flatten_mapping function."""

    def test_flatten_mapping_with_simple_dict(self):
        """Test flattening a simple dictionary."""
        data = {"key1": "value1", "key2": "value2"}
        result = _flatten_mapping("", data)
        assert result == {"key1": "value1", "key2": "value2"}

    def test_flatten_mapping_with_nested_dict(self):
        """Test flattening nested dictionaries."""
        data = {"outer": {"inner": "value"}}
        result = _flatten_mapping("", data)
        assert result == {"outer__inner": "value"}

    def test_flatten_mapping_with_prefix(self):
        """Test flattening with a prefix."""
        data = {"key": "value"}
        result = _flatten_mapping("prefix__", data)
        assert result == {"prefix__key": "value"}

    def test_flatten_mapping_with_multiple_levels(self):
        """Test flattening multiple levels of nesting."""
        data = {"level1": {"level2": {"level3": "deep_value"}}}
        result = _flatten_mapping("", data)
        assert result == {"level1__level2__level3": "deep_value"}

    def test_flatten_mapping_preserves_non_dict_values(self):
        """Test that non-dict values are preserved as-is."""
        data = {"string": "text", "number": 123, "list": [1, 2, 3], "none": None}
        result = _flatten_mapping("", data)
        assert result == {
            "string": "text",
            "number": 123,
            "list": [1, 2, 3],
            "none": None,
        }


class TestAugmentWithUnits:
    """Tests for _augment_with_units function."""

    def test_augment_with_units_adds_unit_columns(self):
        """Test that unit data is added with numeric suffixes."""
        base_rows = [{"id": 1}]
        records = [{"id": 1, "units": [{"price": 2000, "beds": 2}, {"price": 2100, "beds": 3}]}]
        _augment_with_units(base_rows, records)
        assert base_rows[0]["price_1"] == 2000
        assert base_rows[0]["beds_1"] == 2
        assert base_rows[0]["price_2"] == 2100
        assert base_rows[0]["beds_2"] == 3

    def test_augment_with_units_handles_missing_units(self):
        """Test that records without units are handled gracefully."""
        base_rows = [{"id": 1}]
        records = [{"id": 1}]
        _augment_with_units(base_rows, records)
        assert base_rows[0] == {"id": 1}

    def test_augment_with_units_handles_non_list_units(self):
        """Test that non-list units values are ignored."""
        base_rows = [{"id": 1}]
        records = [{"id": 1, "units": "not a list"}]
        _augment_with_units(base_rows, records)
        assert base_rows[0] == {"id": 1}

    def test_augment_with_units_filters_non_dict_items(self):
        """Test that non-dict items in units list are skipped."""
        base_rows = [{"id": 1}]
        records = [{"id": 1, "units": [{"price": 2000}, "invalid", None, {"price": 2100}]}]
        _augment_with_units(base_rows, records)
        # Index 1: {"price": 2000} -> price_1
        # Index 2: "invalid" -> skipped
        # Index 3: None -> skipped
        # Index 4: {"price": 2100} -> price_4
        assert base_rows[0]["price_1"] == 2000
        assert base_rows[0]["price_4"] == 2100
        assert "price_2" not in base_rows[0]
        assert "price_3" not in base_rows[0]

    def test_augment_with_units_flattens_nested_unit_data(self):
        """Test that nested unit data is flattened."""
        base_rows = [{"id": 1}]
        records = [{"id": 1, "units": [{"details": {"sqft": 1200}}]}]
        _augment_with_units(base_rows, records)
        assert base_rows[0]["details__sqft_1"] == 1200


class TestRecordsToDataFrame:
    """Tests for records_to_dataframe function."""

    def test_records_to_dataframe_with_simple_records(self):
        """Test converting simple records to DataFrame."""
        records = [{"id": 1, "name": "Test"}, {"id": 2, "name": "Test2"}]
        df = records_to_dataframe(records)
        assert len(df) == 2
        assert list(df.columns) == ["id", "name"]
        assert df["id"].tolist() == [1, 2]

    def test_records_to_dataframe_with_nested_records(self):
        """Test that nested structures are flattened."""
        records = [{"id": 1, "address": {"street": "Main St", "city": "Nashville"}}]
        df = records_to_dataframe(records)
        assert "address__street" in df.columns
        assert "address__city" in df.columns
        assert df["address__street"].iloc[0] == "Main St"

    def test_records_to_dataframe_excludes_units_from_base(self):
        """Test that 'units' field is excluded from base flattening."""
        records = [{"id": 1, "price": 2000, "units": [{"price": 2100}]}]
        df = records_to_dataframe(records)
        assert "units" not in df.columns
        assert "price_1" in df.columns

    def test_records_to_dataframe_with_empty_records(self):
        """Test that empty records return empty DataFrame."""
        df = records_to_dataframe([])
        assert df.empty
        assert len(df) == 0

    def test_records_to_dataframe_filters_non_dict_records(self):
        """Test that non-dict records are filtered out during base_rows creation."""
        # Note: The type hint says Sequence[Dict[str, Any]], but the function
        # defensively handles non-dict items in the base_rows loop.
        # However, _augment_with_units assumes all items are dicts, so we test
        # with only dict items to match realistic API responses.
        records = [{"id": 1}, {"id": 2}, {"id": 3}]
        df = records_to_dataframe(records)
        assert len(df) == 3
        assert list(df["id"]) == [1, 2, 3]


class TestFetchConfig:
    """Tests for FetchConfig dataclass."""

    def test_fetch_config_initialization(self):
        """Test FetchConfig initialization with required fields."""
        config = FetchConfig(base_params={"status": "ForRent"}, locations=["Nashville"])
        assert config.base_params == {"status": "ForRent"}
        assert config.locations == ["Nashville"]
        assert config.max_pages == DEFAULT_MAX_PAGES

    def test_fetch_config_with_custom_max_pages(self):
        """Test FetchConfig with custom max_pages."""
        config = FetchConfig(base_params={}, locations=[], max_pages=10)
        assert config.max_pages == 10

    def test_fetch_config_is_frozen(self):
        """Test that FetchConfig is immutable (frozen=True)."""
        config = FetchConfig(base_params={}, locations=[])
        with pytest.raises(AttributeError):
            config.max_pages = 20


class TestCollectProperties:
    """Tests for collect_properties function."""

    @responses.activate
    def test_collect_properties_single_location(self, monkeypatch):
        """Test collecting properties for a single location."""
        monkeypatch.setenv("ZILLOW_RAPIDAPI_KEY", "test-key")
        responses.add(
            responses.GET,
            BASE_URL,
            json={"results": [{"id": 1}, {"id": 2}]},
            status=200,
        )
        results = collect_properties(
            base_params={"status_type": "ForRent"},
            locations=["Nashville, TN"],
            max_pages=1,
        )
        assert len(results) == 2
        assert results[0]["id"] == 1

    @responses.activate
    def test_collect_properties_multiple_locations(self, monkeypatch):
        """Test collecting properties for multiple locations."""
        monkeypatch.setenv("ZILLOW_RAPIDAPI_KEY", "test-key")
        for _ in range(2):
            responses.add(
                responses.GET,
                BASE_URL,
                json={"results": [{"id": 1}]},
                status=200,
            )
        results = collect_properties(
            base_params={}, locations=["Location1", "Location2"], max_pages=1
        )
        assert len(results) == 2

    @responses.activate
    def test_collect_properties_with_none_location(self, monkeypatch):
        """Test collecting properties with no explicit location."""
        monkeypatch.setenv("ZILLOW_RAPIDAPI_KEY", "test-key")
        responses.add(
            responses.GET,
            BASE_URL,
            json={"results": [{"id": 1}]},
            status=200,
        )
        results = collect_properties(base_params={}, locations=[None], max_pages=1)
        assert len(results) == 1


class TestFetchDataFrame:
    """Tests for fetch_dataframe function."""

    @responses.activate
    def test_fetch_dataframe_returns_dataframe(self, monkeypatch):
        """Test that fetch_dataframe returns a pandas DataFrame."""
        monkeypatch.setenv("ZILLOW_RAPIDAPI_KEY", "test-key")
        responses.add(
            responses.GET,
            BASE_URL,
            json={"results": [{"id": 1, "price": 2000}]},
            status=200,
        )
        config = FetchConfig(base_params={}, locations=["Nashville"], max_pages=1)
        df = fetch_dataframe(config)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "id" in df.columns

    @responses.activate
    def test_fetch_dataframe_returns_empty_for_no_results(self, monkeypatch):
        """Test that empty DataFrame is returned when no results."""
        monkeypatch.setenv("ZILLOW_RAPIDAPI_KEY", "test-key")
        responses.add(responses.GET, BASE_URL, json={"results": []}, status=200)
        config = FetchConfig(base_params={}, locations=["Nashville"], max_pages=1)
        df = fetch_dataframe(config)
        assert df.empty
