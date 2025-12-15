"""Weekend detection application service."""

from datetime import datetime

from src.domain.services import WeekendDetectionService


def detect_weekend_extractions(
    start_date: datetime, end_date: datetime
) -> list[dict[str, str]]:
    """Detect weekends in date range and return additional extractions.

    This is a convenience wrapper around WeekendDetectionService.

    Args:
        start_date: Start date of the range.
        end_date: End date of the range.

    Returns:
        List of dictionaries with format {'checkin': 'YYYY-MM-DD', 'checkout': 'YYYY-MM-DD'}.
    """
    return WeekendDetectionService.detect_weekend_extractions(start_date, end_date)

