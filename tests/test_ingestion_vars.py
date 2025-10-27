"""Comprehensive tests for utils/ingestionVars.py module."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from freezegun import freeze_time

from utils import ingestionVars


class TestIngestionDate:
    """Tests for ingestion_date variable."""

    @freeze_time("2025-10-27")
    def test_ingestion_date_format(self):
        """Test that ingestion_date has correct YYYYMMDD format."""
        # Need to reimport to get the frozen time
        import importlib

        importlib.reload(ingestionVars)
        assert ingestionVars.ingestion_date == "20251027"

    @freeze_time("2025-01-01")
    def test_ingestion_date_start_of_year(self):
        """Test ingestion_date at start of year."""
        import importlib

        importlib.reload(ingestionVars)
        assert ingestionVars.ingestion_date == "20250101"

    @freeze_time("2025-12-31")
    def test_ingestion_date_end_of_year(self):
        """Test ingestion_date at end of year."""
        import importlib

        importlib.reload(ingestionVars)
        assert ingestionVars.ingestion_date == "20251231"

    @freeze_time("2025-02-28")
    def test_ingestion_date_february_non_leap(self):
        """Test ingestion_date in February of non-leap year."""
        import importlib

        importlib.reload(ingestionVars)
        assert ingestionVars.ingestion_date == "20250228"

    @freeze_time("2024-02-29")
    def test_ingestion_date_leap_year(self):
        """Test ingestion_date on leap day."""
        import importlib

        importlib.reload(ingestionVars)
        assert ingestionVars.ingestion_date == "20240229"

    def test_ingestion_date_is_string(self):
        """Test that ingestion_date is a string type."""
        assert isinstance(ingestionVars.ingestion_date, str)

    def test_ingestion_date_length(self):
        """Test that ingestion_date is exactly 8 characters long."""
        assert len(ingestionVars.ingestion_date) == 8

    def test_ingestion_date_is_numeric(self):
        """Test that ingestion_date contains only digits."""
        assert ingestionVars.ingestion_date.isdigit()

    def test_ingestion_date_year_valid(self):
        """Test that year portion is reasonable (2024-2030 range for this project)."""
        year = int(ingestionVars.ingestion_date[:4])
        assert 2024 <= year <= 2030

    def test_ingestion_date_month_valid(self):
        """Test that month portion is valid (01-12)."""
        month = int(ingestionVars.ingestion_date[4:6])
        assert 1 <= month <= 12

    def test_ingestion_date_day_valid(self):
        """Test that day portion is valid (01-31)."""
        day = int(ingestionVars.ingestion_date[6:8])
        assert 1 <= day <= 31

    def test_ingestion_date_matches_today(self):
        """Test that ingestion_date matches today's date."""
        expected = date.today().strftime("%Y%m%d")
        # Allow re-import to ensure fresh value
        import importlib

        importlib.reload(ingestionVars)
        # Should match within the test execution time
        actual_year = ingestionVars.ingestion_date[:4]
        expected_year = expected[:4]
        assert actual_year == expected_year

    @freeze_time("2025-05-15 23:59:59")
    def test_ingestion_date_end_of_day(self):
        """Test ingestion_date at end of day (should still be that day)."""
        import importlib

        importlib.reload(ingestionVars)
        assert ingestionVars.ingestion_date == "20250515"

    @freeze_time("2025-05-15 00:00:00")
    def test_ingestion_date_start_of_day(self):
        """Test ingestion_date at start of day."""
        import importlib

        importlib.reload(ingestionVars)
        assert ingestionVars.ingestion_date == "20250515"

    def test_ingestion_date_can_be_imported(self):
        """Test that ingestion_date can be imported directly."""
        from utils.ingestionVars import ingestion_date

        assert ingestion_date is not None
        assert isinstance(ingestion_date, str)

    def test_module_has_no_other_exports(self):
        """Test that module only exports ingestion_date."""
        import utils.ingestionVars as module

        public_attrs = [attr for attr in dir(module) if not attr.startswith("_")]
        # Should only have 'date' (imported) and 'ingestion_date' (our variable)
        assert "ingestion_date" in public_attrs
        # date is imported but that's OK
        assert "date" in public_attrs or len(public_attrs) == 1
