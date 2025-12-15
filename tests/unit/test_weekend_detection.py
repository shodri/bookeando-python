"""Unit tests for weekend detection service."""

from datetime import datetime, timedelta

import pytest

from src.domain.services import WeekendDetectionService


class TestWeekendDetectionService:
    """Test cases for WeekendDetectionService."""

    def test_detect_weekend_extractions_friday(self) -> None:
        """Test detecting Friday check-in."""
        # Create a Friday date
        friday = datetime(2024, 1, 5)  # Friday
        end_date = friday + timedelta(days=7)

        result = WeekendDetectionService.detect_weekend_extractions(friday, end_date)

        assert len(result) > 0
        # Should have Friday -> Sunday extraction
        friday_extraction = next(
            (r for r in result if r["checkin"] == friday.strftime("%Y-%m-%d")), None
        )
        assert friday_extraction is not None
        assert friday_extraction["checkout"] == (friday + timedelta(days=2)).strftime(
            "%Y-%m-%d"
        )

    def test_detect_weekend_extractions_saturday(self) -> None:
        """Test detecting Saturday check-in."""
        # Create a Saturday date
        saturday = datetime(2024, 1, 6)  # Saturday
        end_date = saturday + timedelta(days=7)

        result = WeekendDetectionService.detect_weekend_extractions(saturday, end_date)

        assert len(result) > 0
        # Should have Saturday -> Monday extraction
        saturday_extraction = next(
            (r for r in result if r["checkin"] == saturday.strftime("%Y-%m-%d")), None
        )
        assert saturday_extraction is not None
        assert saturday_extraction["checkout"] == (
            saturday + timedelta(days=2)
        ).strftime("%Y-%m-%d")

    def test_detect_weekend_extractions_no_weekends(self) -> None:
        """Test with date range that has no weekends."""
        # Monday to Wednesday
        monday = datetime(2024, 1, 1)  # Monday
        wednesday = datetime(2024, 1, 3)  # Wednesday

        result = WeekendDetectionService.detect_weekend_extractions(monday, wednesday)

        assert len(result) == 0

    def test_detect_weekend_extractions_multiple_weekends(self) -> None:
        """Test detecting multiple weekends in a range."""
        # Start on a Friday, end 2 weeks later
        friday = datetime(2024, 1, 5)  # Friday
        end_date = friday + timedelta(days=14)

        result = WeekendDetectionService.detect_weekend_extractions(friday, end_date)

        # Should have at least 2 weekend extractions
        assert len(result) >= 2

    def test_detect_weekend_extractions_same_day(self) -> None:
        """Test with start and end date being the same."""
        date = datetime(2024, 1, 5)  # Friday

        result = WeekendDetectionService.detect_weekend_extractions(date, date)

        # Should still detect Friday
        assert len(result) == 1
        assert result[0]["checkin"] == date.strftime("%Y-%m-%d")

