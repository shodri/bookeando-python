"""Orchestrator for updating hotel prices via scraping."""

import logging
from datetime import datetime, timedelta
from typing import Any

from mysql.connector import MySQLConnection

from src.config.settings import settings
from src.domain.exceptions import DatabaseConnectionError, DatabaseQueryError, ScrapingError
from src.domain.models import ScrapeSession
from src.infrastructure.database.connection import get_db_connection
from src.infrastructure.database.repositories import (
    HotelRepository,
    RoomRepository,
    ScrapeSessionRepository,
)
from src.infrastructure.scraping.booking_scraper import BookingScraper

logger = logging.getLogger(__name__)


class UpdatePricesService:
    """Service for updating hotel prices through scraping."""

    def __init__(self, connection: MySQLConnection, proxy: str | None = None) -> None:
        """Initialize the service.

        Args:
            connection: Database connection.
            proxy: Optional proxy URL.
        """
        self.conn = connection
        self.proxy = proxy
        self.hotel_repo = HotelRepository(connection)
        self.room_repo = RoomRepository(connection)
        self.session_repo = ScrapeSessionRepository(connection)

    def update_hotel_prices(
        self,
        hotel_id: int,
        hotel_url: str,
        checkin_date: str,
        checkout_date: str,
        adults: int = 1,
        children: int = 0,
        currency: str | None = None,
        extraction_mode: str = "daily",
        proxy_id: int | None = None,
    ) -> dict[str, Any]:
        """Update hotel prices by scraping and saving to database.

        Args:
            hotel_id: Hotel ID.
            hotel_url: Hotel URL on Booking.com.
            checkin_date: Check-in date (YYYY-MM-DD).
            checkout_date: Check-out date (YYYY-MM-DD).
            adults: Number of adults.
            children: Number of children.
            currency: Currency code (defaults to settings.booking_currency).
            extraction_mode: Extraction mode ('daily' or 'restriction').
            proxy_id: Optional proxy ID.

        Returns:
            Dictionary with results: sessions_created, sessions_updated,
            room_availabilities_created, errors.

        Raises:
            ScrapingError: If scraping fails.
            DatabaseQueryError: If database operations fail.
        """
        if currency is None:
            currency = settings.booking_currency

        results = {
            "sessions_created": 0,
            "sessions_updated": 0,
            "room_availabilities_created": 0,
            "errors": [],
        }

        logger.info(
            f"Starting scraping for hotel {hotel_id} - "
            f"Check-in: {checkin_date} to Check-out: {checkout_date}"
        )

        # Scrape hotel data
        scraper = BookingScraper(proxy=self.proxy)
        try:
            scraped_data = scraper.scrape_hotel(
                hotel_url=hotel_url,
                checkin_date=checkin_date,
                checkout_date=checkout_date,
                adults=adults,
                children=children,
                currency=currency,
            )

            if not scraped_data.success:
                error_msg = scraped_data.error_message or "Unknown scraping error"
                results["errors"].append(error_msg)
                logger.error(f"Scraping failed for hotel {hotel_id}: {error_msg}")
                return results

            # Create or update scrape session
            session = ScrapeSession(
                hotel_id=hotel_id,
                checkin_date=checkin_date,
                checkout_date=checkout_date,
                capture_date=scraped_data.capture_date,
                url_requested=hotel_url,
                adults=adults,
                children=children,
                currency=currency,
                success=True,
                room_types_found=len(scraped_data.room_availabilities),
                proxy_id=proxy_id,
            )

            request_params = {
                "checkin_date": checkin_date,
                "checkout_date": checkout_date,
                "adults": adults,
                "children": children,
                "currency": currency,
                "extraction_mode": extraction_mode,
            }

            # Check if session exists
            existing_session_id = self.session_repo.find_existing(
                hotel_id, checkin_date, checkout_date
            )

            if existing_session_id:
                # Update existing session
                self.session_repo.update(existing_session_id, session, request_params)
                results["sessions_updated"] = 1
                session_id = existing_session_id
                logger.info(
                    f"Updated existing scrape session {session_id} for hotel {hotel_id}"
                )
            else:
                # Create new session
                session_id = self.session_repo.create(session, request_params)
                results["sessions_created"] = 1
                logger.info(
                    f"Created new scrape session {session_id} for hotel {hotel_id}"
                )

            # Save room availabilities
            for room_availability in scraped_data.room_availabilities:
                try:
                    # Find or create room type
                    room_type_id = self.room_repo.find_or_create(
                        hotel_id=hotel_id,
                        room_name=room_availability.room_type_name,
                        description="",
                    )

                    # Create room availability
                    self.session_repo.create_room_availability(
                        scrape_session_id=session_id,
                        room_type_id=room_type_id,
                        availability=room_availability.availability,
                        base_price=room_availability.base_price,
                        final_price=room_availability.final_price,
                        offer=room_availability.offer,
                        non_refundable=room_availability.non_refundable,
                    )

                    results["room_availabilities_created"] += 1
                except Exception as e:
                    error_msg = (
                        f"Error processing room {room_availability.room_type_name}: {str(e)}"
                    )
                    results["errors"].append(error_msg)
                    logger.error(f"Error processing room for hotel {hotel_id}: {e}")

            logger.info(
                f"Completed scraping for hotel {hotel_id} - "
                f"Created {results['room_availabilities_created']} room availabilities"
            )

        except Exception as e:
            error_msg = f"Error updating prices for hotel {hotel_id}: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
            raise ScrapingError(error_msg) from e
        finally:
            scraper.close()

        return results

    def update_hotel_for_date_range(
        self,
        hotel_id: int,
        hotel_url: str,
        start_date: datetime,
        end_date: datetime,
        adults: int = 1,
        children: int = 0,
        currency: str | None = None,
        proxy_id: int | None = None,
    ) -> dict[str, Any]:
        """Update hotel prices for a date range.

        Args:
            hotel_id: Hotel ID.
            hotel_url: Hotel URL on Booking.com.
            start_date: Start date.
            end_date: End date.
            adults: Number of adults.
            children: Number of children.
            currency: Currency code.
            proxy_id: Optional proxy ID.

        Returns:
            Aggregated results from all date updates.
        """
        total_results = {
            "sessions_created": 0,
            "sessions_updated": 0,
            "room_availabilities_created": 0,
            "errors": [],
        }

        current_date = start_date
        while current_date <= end_date:
            checkin_date = current_date.strftime("%Y-%m-%d")
            checkout_date = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")

            try:
                results = self.update_hotel_prices(
                    hotel_id=hotel_id,
                    hotel_url=hotel_url,
                    checkin_date=checkin_date,
                    checkout_date=checkout_date,
                    adults=adults,
                    children=children,
                    currency=currency,
                    extraction_mode="daily",
                    proxy_id=proxy_id,
                )

                total_results["sessions_created"] += results["sessions_created"]
                total_results["sessions_updated"] += results["sessions_updated"]
                total_results["room_availabilities_created"] += results[
                    "room_availabilities_created"
                ]
                total_results["errors"].extend(results["errors"])

            except Exception as e:
                error_msg = f"Error updating prices for date {checkin_date}: {str(e)}"
                total_results["errors"].append(error_msg)
                logger.error(error_msg)

            current_date += timedelta(days=1)

        return total_results

