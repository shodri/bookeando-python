"""Database repositories for domain entities."""

import json
from typing import Any

import mysql.connector
from mysql.connector import MySQLConnection

from src.domain.exceptions import DatabaseQueryError
from src.domain.models import Hotel, Room, ScrapeSession
from src.utils.timezone import now_argentina_str


class HotelRepository:
    """Repository for Hotel entities."""

    def __init__(self, connection: MySQLConnection):
        """Initialize repository with database connection.

        Args:
            connection: MySQL connection object.
        """
        self.conn = connection

    def fetch_all(self, limit: int = 100) -> list[Hotel]:
        """Fetch all hotels from database.

        Args:
            limit: Maximum number of hotels to fetch.

        Returns:
            List of Hotel domain objects.

        Raises:
            DatabaseQueryError: If query fails.
        """
        cur = self.conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM hotels LIMIT %s", (limit,))
            rows = cur.fetchall()
            return [Hotel.from_dict(row) for row in rows]
        except mysql.connector.Error as e:
            raise DatabaseQueryError(f"Failed to fetch hotels: {e}") from e
        finally:
            cur.close()

    def get_random_proxy(self) -> str | None:
        """Get a random proxy from the database.

        Returns:
            Proxy URL in format "http://ip_address:port" or None if no proxies available.

        Raises:
            DatabaseQueryError: If query fails.
        """
        cur = self.conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT ip_address, port FROM proxies ORDER BY RAND() LIMIT 1")
            row = cur.fetchone()

            if row and row.get("ip_address") and row.get("port"):
                ip_address = row["ip_address"]
                port = row["port"]
                return f"http://{ip_address}:{port}"
            return None
        except mysql.connector.Error as e:
            raise DatabaseQueryError(f"Failed to fetch proxy: {e}") from e
        finally:
            cur.close()


class RoomRepository:
    """Repository for Room entities."""

    def __init__(self, connection: MySQLConnection):
        """Initialize repository with database connection.

        Args:
            connection: MySQL connection object.
        """
        self.conn = connection

    def find_or_create(self, hotel_id: int, room_name: str, description: str = "") -> int:
        """Find or create a room type.

        Args:
            hotel_id: Hotel ID.
            room_name: Room type name.
            description: Room type description.

        Returns:
            Room type ID.

        Raises:
            DatabaseQueryError: If query fails.
        """
        name = room_name.strip()
        if not name:
            raise ValueError("Room name cannot be empty")

        cur = self.conn.cursor()
        try:
            # Try to find existing room type
            cur.execute(
                "SELECT id FROM room_types WHERE hotel_id=%s AND LOWER(name)=LOWER(%s) LIMIT 1",
                (hotel_id, name),
            )
            row = cur.fetchone()

            if row:
                return row[0]

            # Create new room type
            now = now_argentina_str()
            cur.execute(
                "INSERT INTO room_types (hotel_id, name, description, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (hotel_id, name, description, now, now),
            )
            self.conn.commit()
            return cur.lastrowid
        except mysql.connector.Error as e:
            self.conn.rollback()
            raise DatabaseQueryError(f"Failed to find or create room type: {e}") from e
        finally:
            cur.close()


class ScrapeSessionRepository:
    """Repository for ScrapeSession entities."""

    def __init__(self, connection: MySQLConnection):
        """Initialize repository with database connection.

        Args:
            connection: MySQL connection object.
        """
        self.conn = connection

    def find_existing(
        self, hotel_id: int, checkin_date: str, checkout_date: str
    ) -> int | None:
        """Find existing scrape session.

        Args:
            hotel_id: Hotel ID.
            checkin_date: Check-in date (YYYY-MM-DD).
            checkout_date: Check-out date (YYYY-MM-DD).

        Returns:
            Session ID if found, None otherwise.

        Raises:
            DatabaseQueryError: If query fails.
        """
        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT id FROM scrape_sessions WHERE hotel_id=%s AND checkin_date=%s AND checkout_date=%s LIMIT 1",
                (hotel_id, checkin_date, checkout_date),
            )
            row = cur.fetchone()
            return row[0] if row else None
        except mysql.connector.Error as e:
            raise DatabaseQueryError(f"Failed to find scrape session: {e}") from e
        finally:
            cur.close()

    def create(self, session: ScrapeSession, request_params: dict[str, Any]) -> int:
        """Create a new scrape session.

        Args:
            session: ScrapeSession domain object.
            request_params: Request parameters to store as JSON.

        Returns:
            Created session ID.

        Raises:
            DatabaseQueryError: If insert fails.
        """
        cur = self.conn.cursor()
        try:
            session_dict = session.to_dict()
            capture_date = session_dict["capture_date"]
            request_params_json = json.dumps(request_params, ensure_ascii=False)

            cur.execute(
                """INSERT INTO scrape_sessions
                    (hotel_id, proxy_id, checkin_date, checkout_date, adults, children, currency,
                     capture_date, url_requested, response_status, request_params, error_message,
                     success, notes, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    session_dict["hotel_id"],
                    session_dict["proxy_id"],
                    session_dict["checkin_date"],
                    session_dict["checkout_date"],
                    session_dict["adults"],
                    session_dict["children"],
                    session_dict["currency"],
                    capture_date,
                    session_dict["url_requested"],
                    None,  # response_status
                    request_params_json,
                    session_dict["error_message"],
                    session_dict["success"],
                    None,  # notes
                    capture_date,
                    capture_date,
                ),
            )
            new_id = cur.lastrowid

            # Try to update additional fields if they exist
            try:
                cur.execute(
                    "UPDATE scrape_sessions SET room_types_found=%s WHERE id=%s",
                    (session_dict["room_types_found"], new_id),
                )
            except mysql.connector.Error:
                pass  # Field may not exist

            self.conn.commit()
            return new_id
        except mysql.connector.Error as e:
            self.conn.rollback()
            raise DatabaseQueryError(f"Failed to create scrape session: {e}") from e
        finally:
            cur.close()

    def update(
        self, session_id: int, session: ScrapeSession, request_params: dict[str, Any]
    ) -> None:
        """Update an existing scrape session.

        Args:
            session_id: Session ID to update.
            session: ScrapeSession domain object with updated data.
            request_params: Request parameters to store as JSON.

        Raises:
            DatabaseQueryError: If update fails.
        """
        cur = self.conn.cursor()
        try:
            session_dict = session.to_dict()
            capture_date = session_dict["capture_date"]
            request_params_json = json.dumps(request_params, ensure_ascii=False)

            cur.execute(
                """UPDATE scrape_sessions SET
                    proxy_id=%s, capture_date=%s, adults=%s, children=%s, currency=%s,
                    url_requested=%s, response_status=%s, request_params=%s, error_message=%s,
                    success=%s, notes=%s, updated_at=%s
                    WHERE id=%s""",
                (
                    session_dict["proxy_id"],
                    capture_date,
                    session_dict["adults"],
                    session_dict["children"],
                    session_dict["currency"],
                    session_dict["url_requested"],
                    None,  # response_status
                    request_params_json,
                    session_dict["error_message"],
                    session_dict["success"],
                    None,  # notes
                    capture_date,
                    session_id,
                ),
            )

            # Try to update additional fields if they exist
            try:
                cur.execute(
                    "UPDATE scrape_sessions SET room_types_found=%s WHERE id=%s",
                    (session_dict["room_types_found"], session_id),
                )
            except mysql.connector.Error:
                pass  # Field may not exist

            self.conn.commit()
        except mysql.connector.Error as e:
            self.conn.rollback()
            raise DatabaseQueryError(f"Failed to update scrape session: {e}") from e
        finally:
            cur.close()

    def create_room_availability(
        self,
        scrape_session_id: int,
        room_type_id: int,
        availability: int | None,
        base_price: float,
        final_price: float,
        offer: str | None = None,
        non_refundable: bool = False,
    ) -> None:
        """Create a room availability record.

        Args:
            scrape_session_id: Scrape session ID.
            room_type_id: Room type ID.
            availability: Number of available rooms.
            base_price: Base price.
            final_price: Final price.
            offer: Offer text.
            non_refundable: Whether the room is non-refundable.

        Raises:
            DatabaseQueryError: If insert fails.
        """
        cur = self.conn.cursor()
        try:
            now = now_argentina_str()
            cur.execute(
                """INSERT INTO room_availabilities
                    (scrape_session_id, room_type_id, room_available_count, offer, base_price,
                     final_price, non_refundable, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    scrape_session_id,
                    room_type_id,
                    availability,
                    offer,
                    base_price,
                    final_price,
                    1 if non_refundable else 0,
                    now,
                    now,
                ),
            )
            self.conn.commit()
        except mysql.connector.Error as e:
            self.conn.rollback()
            raise DatabaseQueryError(f"Failed to create room availability: {e}") from e
        finally:
            cur.close()

