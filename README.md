# Booking Scraper v5 - Enterprise Edition

A refactored, enterprise-grade Booking.com scraper following clean architecture principles.

## Architecture

The project follows **Hexagonal Architecture** (Ports & Adapters) with clear separation of concerns:

```
src/
├── domain/              # Pure business logic (no external dependencies)
│   ├── models.py        # Domain models (dataclasses)
│   ├── exceptions.py    # Custom domain exceptions
│   └── services.py      # Business logic services
├── infrastructure/      # External implementations
│   ├── database/        # Database repositories
│   ├── scraping/       # Selenium scraping implementation
│   └── logging/         # Structured logging setup
├── application/         # Use cases and orchestration
│   ├── update_prices.py
│   └── weekend_detector.py
└── main.py              # Entry point
```

## Features

- ✅ **PEP 8 Compliant**: Code formatted with Black/Ruff
- ✅ **Type Hints**: Full type annotations with mypy validation
- ✅ **Environment Variables**: Secure configuration via `.env` and Pydantic Settings
- ✅ **Structured Logging**: JSON logging for production monitoring
- ✅ **Custom Exceptions**: Domain-specific error handling
- ✅ **Unit Tests**: Comprehensive test coverage with pytest
- ✅ **Clean Architecture**: Separation of concerns (Domain/Infrastructure/Application)

## Setup

### 1. Install Dependencies

Using Poetry (recommended):
```bash
poetry install
```

Or using pip:
```bash
pip install -r requirements.txt  # If you create one from pyproject.toml
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your database credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```env
DB_HOST=your_host
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=bookeandov5
```

### 3. Run the Scraper

```bash
python -m src.main --days 15
```

## Development

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit

# Integration tests only
pytest tests/integration

# With coverage
pytest --cov=src --cov-report=html
```

### Code Formatting

```bash
# Format with Black
black src tests

# Lint with Ruff
ruff check src tests

# Type checking with mypy
mypy src
```

## Project Structure

### Domain Layer (`src/domain/`)

Pure business logic with no external dependencies:

- **models.py**: Immutable dataclasses (Hotel, Room, ScrapeSession, etc.)
- **exceptions.py**: Custom exception hierarchy
- **services.py**: Business logic (price cleaning, weekend detection, etc.)

### Infrastructure Layer (`src/infrastructure/`)

External implementations:

- **database/**: MySQL repositories (HotelRepository, RoomRepository, etc.)
- **scraping/**: Selenium-based scraper (no database logic)
- **logging/**: Structured JSON logging configuration

### Application Layer (`src/application/`)

Use cases and orchestration:

- **update_prices.py**: Orchestrates scraping → database saving
- **weekend_detector.py**: Weekend extraction detection

## Configuration

All configuration is managed through environment variables (see `.env.example`):

- Database connection settings
- Logging configuration (JSON/text format)
- Scraping delays and timeouts
- Chrome/ChromeDriver settings

## Testing

The project includes:

- **Unit Tests**: Test business logic in isolation
- **Integration Tests**: Test with mocked Selenium and database

Run tests with:
```bash
pytest
```

## Migration from Old Code

The old `booking_scraper.py` file is kept for backward compatibility but is deprecated. New code should use:

- `src.main` for the entry point
- `src.application.UpdatePricesService` for scraping orchestration
- `src.infrastructure.scraping.BookingScraper` for scraping only

## License

[Your License Here]

