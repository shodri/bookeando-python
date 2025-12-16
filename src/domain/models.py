"""Domain models (dataclasses)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Hotel:
    """Hotel domain model."""

    id: int
    name: str
    url: str
    slug: str | None = None
    currency: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Hotel":
        """Create Hotel from dictionary."""
        slug = data.get("url", "").split("/")[-1].split(".")[0] if data.get("url") else None
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            url=data.get("url", ""),
            slug=slug,
            currency=data.get("currency"),
        )


@dataclass(frozen=True)
class Room:
    """Room type domain model."""

    id: int | None
    hotel_id: int
    name: str
    description: str = ""


@dataclass(frozen=True)
class Price:
    """Price domain model."""

    base_price: float
    final_price: float
    currency: str = "EUR"


@dataclass
class RoomAvailability:
    """Room availability domain model."""

    room_type_id: int
    room_type_name: str
    base_price: float
    final_price: float
    availability: int | None
    offer: str | None = None
    non_refundable: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.room_type_name,
            "base_price": self.base_price,
            "final_price": self.final_price,
            "availability": self.availability,
            "offer": self.offer,
            "non_refundable": self.non_refundable,
        }


@dataclass
class ScrapeSession:
    """Scraping session domain model."""

    hotel_id: int
    checkin_date: str
    checkout_date: str
    capture_date: datetime
    url_requested: str
    adults: int = 1
    children: int = 0
    currency: str = "EUR"
    success: bool = False
    error_message: str | None = None
    room_types_found: int = 0
    proxy_id: int | None = None
    id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database operations."""
        return {
            "hotel_id": self.hotel_id,
            "checkin_date": self.checkin_date,
            "checkout_date": self.checkout_date,
            "capture_date": self.capture_date.strftime("%Y-%m-%d %H:%M:%S"),
            "url_requested": self.url_requested,
            "adults": self.adults,
            "children": self.children,
            "currency": self.currency,
            "success": 1 if self.success else 0,
            "error_message": self.error_message,
            "room_types_found": self.room_types_found,
            "proxy_id": self.proxy_id,
        }


@dataclass
class ScrapedHotelData:
    """Scraped hotel data domain model."""

    hotel_url: str
    checkin_date: str
    checkout_date: str
    capture_date: datetime
    room_availabilities: list[RoomAvailability] = field(default_factory=list)
    success: bool = False
    error_message: str | None = None
    adults: int = 1
    children: int = 0
    currency: str = "EUR"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "date": self.checkin_date,
            "capture_date": self.capture_date.isoformat(),
            "hotel": self.hotel_url,
            "checkin_date": self.checkin_date,
            "checkout_date": self.checkout_date,
            "adults": self.adults,
            "children": self.children,
            "currency": self.currency,
            "room_types": [room.to_dict() for room in self.room_availabilities],
            "success": self.success,
        }

