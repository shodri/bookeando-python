"""Business logic services."""

import re
from datetime import datetime, timedelta
from typing import Any


class PriceService:
    """Service for price-related business logic."""

    @staticmethod
    def clean_price(price_text: str | None) -> float:
        """Clean and convert price text to float.

        Args:
            price_text: Price text that may contain currency symbols and separators.

        Returns:
            Cleaned price as float, or 0.0 if invalid.
        """
        if not price_text:
            return 0.0

        # Remove currency symbols and thousand separators
        clean = re.sub(r"[^\d,]", "", price_text)
        clean = clean.replace(",", ".")

        try:
            return float(clean)
        except ValueError:
            return 0.0


class TextExtractionService:
    """Service for text extraction operations."""

    @staticmethod
    def extract_number(text: str | None) -> int | None:
        """Extract first number from text.

        Args:
            text: Text that may contain numbers.

        Returns:
            First integer found, or None if no number found.
        """
        if not text:
            return None

        match = re.search(r"\d+", text)
        return int(match.group()) if match else None


class WeekendDetectionService:
    """Service for weekend extraction detection."""

    @staticmethod
    def detect_weekend_extractions(
        start_date: datetime, end_date: datetime
    ) -> list[dict[str, str]]:
        """Detect weekends in date range and return additional extractions.

        Detects:
        - Friday check-in → Sunday check-out (2 days)
        - Saturday check-in → Monday check-out (2 days)

        Args:
            start_date: Start date of the range.
            end_date: End date of the range.

        Returns:
            List of dictionaries with format {'checkin': 'YYYY-MM-DD', 'checkout': 'YYYY-MM-DD'}.
        """
        weekend_extractions: list[dict[str, str]] = []
        current_date = start_date

        # Iterate over date range
        while current_date <= end_date:
            weekday = current_date.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday

            # Detect Friday (weekday == 4)
            if weekday == 4:  # Friday
                checkout_date = current_date + timedelta(days=2)  # Sunday
                # Only add if check-in is within range
                if current_date <= end_date:
                    weekend_extractions.append(
                        {
                            "checkin": current_date.strftime("%Y-%m-%d"),
                            "checkout": checkout_date.strftime("%Y-%m-%d"),
                        }
                    )

            # Detect Saturday (weekday == 5)
            elif weekday == 5:  # Saturday
                checkout_date = current_date + timedelta(days=2)  # Monday
                # Only add if check-in is within range
                if current_date <= end_date:
                    weekend_extractions.append(
                        {
                            "checkin": current_date.strftime("%Y-%m-%d"),
                            "checkout": checkout_date.strftime("%Y-%m-%d"),
                        }
                    )

            current_date += timedelta(days=1)

        return weekend_extractions

