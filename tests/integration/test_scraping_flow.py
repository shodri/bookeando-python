"""Integration tests for scraping flow with mocks."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.domain.models import RoomAvailability, ScrapedHotelData
from src.infrastructure.scraping.booking_scraper import BookingScraper


class TestBookingScraperIntegration:
    """Integration tests for BookingScraper with mocked Selenium."""

    @patch("src.infrastructure.scraping.booking_scraper.DriverFactory.create_driver")
    def test_scrape_hotel_success(self, mock_create_driver: MagicMock) -> None:
        """Test successful hotel scraping with mocked driver."""
        # Create mock driver
        mock_driver = Mock()
        mock_element = Mock()
        mock_row = Mock()

        # Mock page source
        mock_driver.page_source = "<html><body>Test</body></html>"

        # Mock find_elements to return rows
        mock_rows = [mock_row] * 3
        mock_driver.find_elements.return_value = mock_rows

        # Mock row attributes
        mock_row.get_attribute.return_value = '<div>Room info</div>'
        mock_row.find_elements.return_value = []

        # Mock WebDriverWait
        mock_create_driver.return_value = (mock_driver, "/tmp/test", 9222)

        scraper = BookingScraper(proxy=None)

        try:
            result = scraper.scrape_hotel(
                hotel_url="https://www.booking.com/hotel/test.html",
                checkin_date="2024-01-01",
                checkout_date="2024-01-02",
            )

            assert isinstance(result, ScrapedHotelData)
            assert result.hotel_url == "https://www.booking.com/hotel/test.html"
            assert result.checkin_date == "2024-01-01"
            assert result.checkout_date == "2024-01-02"
        finally:
            scraper.close()

    @patch("src.infrastructure.scraping.booking_scraper.DriverFactory.create_driver")
    def test_scrape_hotel_with_room_data(self, mock_create_driver: MagicMock) -> None:
        """Test scraping with room data in HTML."""
        # Create mock driver
        mock_driver = Mock()
        mock_row = Mock()

        # Mock HTML with room data
        mock_row.get_attribute.return_value = (
            '<span class="hprt-roomtype-icon-link">Deluxe Room</span>'
            '<div class="bui-f-color-destructive">€100</div>'
            '<span class="prco-valign-middle-helper">€90</span>'
        )

        # Mock room type element
        mock_room_type_element = Mock()
        mock_room_type_element.text = "Deluxe Room"

        # Mock price elements
        mock_base_price_element = Mock()
        mock_base_price_element.text = "€100"
        mock_final_price_element = Mock()
        mock_final_price_element.text = "€90"

        # Mock find_elements calls
        def find_elements_side_effect(selector: str) -> list:
            if "hprt-roomtype-icon-link" in selector:
                return [mock_room_type_element]
            elif "js-strikethrough-price" in selector:
                return [mock_base_price_element]
            elif "prco-valign-middle-helper" in selector:
                return [mock_final_price_element]
            else:
                return []

        mock_row.find_elements.side_effect = find_elements_side_effect
        mock_driver.find_elements.return_value = [mock_row]
        mock_driver.page_source = "<html><body>Test</body></html>"

        mock_create_driver.return_value = (mock_driver, "/tmp/test", 9222)

        scraper = BookingScraper(proxy=None)

        try:
            result = scraper.scrape_hotel(
                hotel_url="https://www.booking.com/hotel/test.html",
                checkin_date="2024-01-01",
                checkout_date="2024-01-02",
            )

            assert isinstance(result, ScrapedHotelData)
            # Should have extracted room data
            assert len(result.room_availabilities) > 0
        finally:
            scraper.close()

    @patch("src.infrastructure.scraping.booking_scraper.DriverFactory.create_driver")
    def test_scrape_hotel_driver_error(self, mock_create_driver: MagicMock) -> None:
        """Test scraping when driver creation fails."""
        from src.domain.exceptions import ScrapingError

        mock_create_driver.side_effect = Exception("Driver creation failed")

        with pytest.raises(ScrapingError):
            BookingScraper(proxy=None)

