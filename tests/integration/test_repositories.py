"""Integration tests for repositories with mocked database."""

from unittest.mock import MagicMock, Mock

import pytest

from src.domain.exceptions import DatabaseQueryError
from src.domain.models import Hotel, ScrapeSession
from src.infrastructure.database.repositories import (
    HotelRepository,
    RoomRepository,
    ScrapeSessionRepository,
)


class TestHotelRepository:
    """Test cases for HotelRepository."""

    def test_fetch_all_success(self) -> None:
        """Test fetching all hotels successfully."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock database response
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Test Hotel", "url": "https://booking.com/hotel/test"},
            {"id": 2, "name": "Another Hotel", "url": "https://booking.com/hotel/another"},
        ]

        repo = HotelRepository(mock_conn)
        hotels = repo.fetch_all(limit=10)

        assert len(hotels) == 2
        assert isinstance(hotels[0], Hotel)
        assert hotels[0].id == 1
        assert hotels[0].name == "Test Hotel"

    def test_fetch_all_database_error(self) -> None:
        """Test fetching hotels when database error occurs."""
        import mysql.connector

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = mysql.connector.Error("Database error")

        repo = HotelRepository(mock_conn)

        with pytest.raises(DatabaseQueryError):
            repo.fetch_all()

    def test_get_random_proxy_success(self) -> None:
        """Test getting random proxy successfully."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock database response
        mock_cursor.fetchone.return_value = {"ip_address": "192.168.1.1", "port": 8080}

        repo = HotelRepository(mock_conn)
        proxy = repo.get_random_proxy()

        assert proxy == "http://192.168.1.1:8080"

    def test_get_random_proxy_no_proxies(self) -> None:
        """Test getting proxy when none available."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock empty response
        mock_cursor.fetchone.return_value = None

        repo = HotelRepository(mock_conn)
        proxy = repo.get_random_proxy()

        assert proxy is None


class TestRoomRepository:
    """Test cases for RoomRepository."""

    def test_find_or_create_existing(self) -> None:
        """Test finding existing room type."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock existing room found
        mock_cursor.fetchone.return_value = (5,)

        repo = RoomRepository(mock_conn)
        room_id = repo.find_or_create(hotel_id=1, room_name="Deluxe Room")

        assert room_id == 5
        # Should not call INSERT
        mock_cursor.execute.assert_called_once()

    def test_find_or_create_new(self) -> None:
        """Test creating new room type."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock no existing room found, then insert
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 10

        repo = RoomRepository(mock_conn)
        room_id = repo.find_or_create(hotel_id=1, room_name="Deluxe Room")

        assert room_id == 10
        # Should call INSERT
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called_once()


class TestScrapeSessionRepository:
    """Test cases for ScrapeSessionRepository."""

    def test_find_existing(self) -> None:
        """Test finding existing scrape session."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor

        # Mock existing session found
        mock_cursor.fetchone.return_value = (15,)

        repo = ScrapeSessionRepository(mock_conn)
        session_id = repo.find_existing(
            hotel_id=1, checkin_date="2024-01-01", checkout_date="2024-01-02"
        )

        assert session_id == 15

    def test_create_new_session(self) -> None:
        """Test creating new scrape session."""
        from datetime import datetime

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 20

        session = ScrapeSession(
            hotel_id=1,
            checkin_date="2024-01-01",
            checkout_date="2024-01-02",
            capture_date=datetime.now(),
            url_requested="https://booking.com/hotel/test",
        )

        repo = ScrapeSessionRepository(mock_conn)
        session_id = repo.create(session, {})

        assert session_id == 20
        mock_conn.commit.assert_called()

