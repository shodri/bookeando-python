"""Timezone utilities for Argentina time."""

from datetime import datetime
from zoneinfo import ZoneInfo

# Timezone de Argentina (UTC-3)
ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def now_argentina() -> datetime:
    """Get current datetime in Argentina timezone.

    Returns:
        Current datetime in Argentina timezone (America/Argentina/Buenos_Aires).
    """
    return datetime.now(ARGENTINA_TZ)


def now_argentina_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Get current datetime in Argentina timezone as formatted string.

    Args:
        fmt: Format string (default: "%Y-%m-%d %H:%M:%S").

    Returns:
        Formatted datetime string in Argentina timezone.
    """
    return now_argentina().strftime(fmt)
