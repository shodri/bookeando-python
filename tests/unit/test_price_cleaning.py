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

    def test_apply_price_increment_positive(self) -> None:
        """Test applying price increment to positive price."""
        # With 10.5% increment, 100 should become 110.5, rounded to 110
        result = PriceService.apply_price_increment(100.0)
        assert result == 110

    def test_apply_price_increment_zero(self) -> None:
        """Test applying price increment to zero."""
        result = PriceService.apply_price_increment(0.0)
        assert result == 0.0

    def test_apply_price_increment_negative(self) -> None:
        """Test applying price increment to negative price."""
        result = PriceService.apply_price_increment(-10.0)
        assert result == 0.0

