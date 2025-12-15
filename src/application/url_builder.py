"""URL builder for Booking.com scraping."""

import hashlib
import time
from urllib.parse import urlencode, quote_plus

from src.config.settings import settings


def build_booking_url(
    hotel_slug: str,
    checkin: str,
    checkout: str,
    currency: str | None = None,
    adults: int = 1,
    children: int = 0,
    country_code: str | None = None,
    language_code: str | None = None,
) -> str:
    """Build Booking.com URL with all required parameters.

    Args:
        hotel_slug: Hotel slug (e.g., "bristol").
        checkin: Check-in date (YYYY-MM-DD).
        checkout: Check-out date (YYYY-MM-DD).
        currency: Currency code (defaults to settings.booking_currency).
        adults: Number of adults.
        children: Number of children.
        country_code: Country code (defaults to settings.booking_country_code).
        language_code: Language code (defaults to settings.booking_language_code).

    Returns:
        Complete Booking.com URL with all parameters.
    """
    if currency is None:
        currency = settings.booking_currency
    if country_code is None:
        country_code = settings.booking_country_code
    if language_code is None:
        language_code = settings.booking_language_code

    # Generate srpvid (16 character MD5 hash of microtime)
    microtime = time.time()
    srpvid = hashlib.md5(str(microtime).encode()).hexdigest()[:16]

    # Build query parameters (only include non-empty values)
    params = {
        "aid": settings.booking_aid,
        "label": settings.booking_label,
        "checkin": checkin,
        "checkout": checkout,
        "dest_type": "hotel",
        "dist": "0",
        "group_adults": str(adults),
        "group_children": str(children),
        "hapos": "1",
        "hpos": "1",
        "no_rooms": "1",
        "req_adults": str(adults),
        "req_children": str(children),
        "room1": "A,A",  # Will be URL-encoded to A%2CA
        "sb_price_type": "total",
        "sr_order": "popularity",
        "srepoch": str(int(time.time())),
        "srpvid": srpvid,
        "type": "total",
        "ucfs": "1",
        "selected_currency": currency,
    }

    # Note: These parameters are set by Booking.com after initial load, 
    # but we include them as empty strings to match the expected format
    # They will be populated by Booking.com's JavaScript:
    # - sid (session ID)
    # - all_sr_blocks
    # - dest_id
    # - highlighted_blocks
    # - matching_block_id
    # - sr_pri_blocks

    # Build URL with country code and language code in slug
    # Format: https://www.booking.com/hotel/{country_code}/{hotel_slug}.{language_code}.html
    base_url = f"https://www.booking.com/hotel/{country_code}/{hotel_slug}.{language_code}.html"
    
    # Use urlencode with quote_via=quote_plus to properly encode special characters
    query_string = urlencode(params, quote_via=quote_plus, safe="")

    return f"{base_url}?{query_string}"

