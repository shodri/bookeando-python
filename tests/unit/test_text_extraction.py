"""Unit tests for text extraction service."""

import pytest

from src.domain.services import TextExtractionService


class TestTextExtractionService:
    """Test cases for TextExtractionService."""

    def test_extract_number_simple(self) -> None:
        """Test extracting number from simple text."""
        result = TextExtractionService.extract_number("Only 5 left")
        assert result == 5

    def test_extract_number_multiple_digits(self) -> None:
        """Test extracting number with multiple digits."""
        result = TextExtractionService.extract_number("Room 123 available")
        assert result == 123

    def test_extract_number_none(self) -> None:
        """Test extracting number from None."""
        result = TextExtractionService.extract_number(None)
        assert result is None

    def test_extract_number_empty_string(self) -> None:
        """Test extracting number from empty string."""
        result = TextExtractionService.extract_number("")
        assert result is None

    def test_extract_number_no_number(self) -> None:
        """Test extracting number when no number present."""
        result = TextExtractionService.extract_number("No numbers here")
        assert result is None

    def test_extract_number_first_number_only(self) -> None:
        """Test that only first number is extracted."""
        result = TextExtractionService.extract_number("5 rooms and 10 beds")
        assert result == 5

