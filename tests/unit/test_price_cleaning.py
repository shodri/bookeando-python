"""Unit tests for price cleaning service."""

import pytest

from src.domain.services import PriceService


class TestPriceService:
    """Test cases for PriceService."""

    def test_clean_price_with_euro_symbol(self) -> None:
        """Test cleaning price with Euro symbol."""
        result = PriceService.clean_price("€150.50")
        assert result == 150.5

    def test_clean_price_with_comma_separator(self) -> None:
        """Test cleaning price with comma as decimal separator."""
        result = PriceService.clean_price("150,50")
        assert result == 150.5

    def test_clean_price_with_thousand_separator(self) -> None:
        """Test cleaning price with thousand separator."""
        result = PriceService.clean_price("1.500,50")
        assert result == 1500.5

    def test_clean_price_none(self) -> None:
        """Test cleaning None price."""
        result = PriceService.clean_price(None)
        assert result == 0.0

    def test_clean_price_empty_string(self) -> None:
        """Test cleaning empty string."""
        result = PriceService.clean_price("")
        assert result == 0.0

    def test_clean_price_invalid(self) -> None:
        """Test cleaning invalid price string."""
        result = PriceService.clean_price("invalid")
        assert result == 0.0

