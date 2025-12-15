"""Custom domain exceptions."""


class ScrapingError(Exception):
    """Base exception for scraping-related errors."""

    pass


class ScrapingNetworkError(ScrapingError):
    """Raised when a network error occurs during scraping."""

    pass


class ScrapingTimeoutError(ScrapingError):
    """Raised when a scraping operation times out."""

    pass


class HotelNotFoundException(ScrapingError):
    """Raised when a hotel is not found."""

    pass


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""

    pass


class DatabaseQueryError(Exception):
    """Raised when a database query fails."""

    pass


class ConfigurationError(Exception):
    """Raised when there's a configuration error."""

    pass

