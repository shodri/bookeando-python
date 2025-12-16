"""Application settings using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    db_host: str = "localhost"
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "bookeando-f4"
    db_port: int = 3306

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"  # 'json' or 'text'
    log_file: str = "logs/scraper.log"

    # Scraping Configuration
    scraping_delay_min: int = 7
    scraping_delay_max: int = 20
    scraping_timeout: int = 30
    headless_mode: bool = False  # Set to True for servers, False to see browser

    # Chrome Configuration
    chrome_debug_port: int = 0
    chrome_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )



    # Booking.com URL Configuration
    booking_currency: str = "EUR"  # Default currency for Booking.com URLs
    booking_country_code: str = "ar"  # Country code (ar, es, etc.)
    booking_language_code: str = "es"  # Language code (es, en, etc.)
    booking_aid: str = "2369661"
    booking_label: str = (
        "msn-yfgP0XnN9y0nVn6Sx32PmQ-79989658705812:"
        "tikwd-79989834229482:aud-811122080:loc-170:neo:mte:lp164493:dec:qsbooking"
    )

    @property
    def db_connection_params(self) -> dict[str, str | int]:
        """Get database connection parameters as a dictionary."""
        return {
            "host": self.db_host,
            "user": self.db_user,
            "password": self.db_password,
            "database": self.db_name,
            "port": self.db_port,
        }


# Global settings instance
settings = Settings()

