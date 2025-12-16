"""Main entry point for the booking scraper."""

import argparse
import logging
import random
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from src.application.update_prices import UpdatePricesService
from src.application.url_builder import build_booking_url
from src.application.weekend_detector import detect_weekend_extractions
from src.config.settings import settings
from src.domain.exceptions import DatabaseConnectionError
from src.infrastructure.database.connection import get_db_connection
from src.infrastructure.database.repositories import HotelRepository
from src.infrastructure.logging.setup import setup_logging

logger = logging.getLogger(__name__)


def kill_chrome_processes() -> None:
    """Kill all Chrome and ChromeDriver processes that may be hanging."""
    try:
        # Kill Chrome processes
        subprocess.run(
            ["pkill", "-9", "-f", "chrome.*--headless"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        # Kill ChromeDriver processes
        subprocess.run(
            ["pkill", "-9", "-f", "chromedriver"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        logger.info("Chrome/ChromeDriver zombie processes eliminated")
    except Exception as e:
        logger.warning(f"Error killing Chrome processes: {e}")


def cleanup_old_temp_dirs(max_age_hours: int = 24) -> None:
    """Clean up old temporary directories that may have been left behind."""
    try:
        import glob
        import os
        import shutil

        temp_base = Path.cwd() / "tmp"
        if not temp_base.exists():
            return

        cleaned = 0
        now = time.time()
        max_age_seconds = max_age_hours * 3600

        for temp_dir in glob.glob(str(temp_base / "tmp*")):
            try:
                # Verify it's a directory
                if os.path.isdir(temp_dir) and temp_dir != str(temp_base):
                    # Check directory age
                    dir_age = now - os.path.getmtime(temp_dir)
                    if dir_age > max_age_seconds:
                        # Verify it's a Chrome temp directory (contains Default)
                        if os.path.exists(os.path.join(temp_dir, "Default")):
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            cleaned += 1
                            logger.debug(f"Old temporary directory removed: {temp_dir}")
            except Exception as e:
                logger.debug(f"Error checking directory {temp_dir}: {e}")
                continue

        if cleaned > 0:
            logger.info(f"Temporary directory cleanup: {cleaned} directories removed")
    except Exception as e:
        logger.warning(f"Error cleaning old temporary directories: {e}")


def main() -> None:
    """Main entry point."""
    # Setup logging
    setup_logging()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Booking Scraper")
    parser.add_argument(
        "--days", type=int, default=15, help="Number of days to extract (default: 15)"
    )
    args = parser.parse_args()

    # Clean up zombie processes and old temp files at startup
    logger.info("🧹 Cleaning Chrome/ChromeDriver zombie processes and old temp files...")
    kill_chrome_processes()
    cleanup_old_temp_dirs(max_age_hours=1)
    logger.info("✅ Initial cleanup completed")

    days_to_extract = args.days
    print(f"📅 Configured to extract {days_to_extract} days")

    # Get list of hotels
    try:
        conn_temp = get_db_connection()
        try:
            hotel_repo = HotelRepository(conn_temp)
            hotels = hotel_repo.fetch_all(limit=1000)

            if not hotels:
                raise RuntimeError("No hotels found in hotels table")

            print(f"📋 Total hotels to process: {len(hotels)}")
        finally:
            conn_temp.close()
    except DatabaseConnectionError as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    # Select proxy once for entire execution
    try:
        conn_proxy = get_db_connection()
        try:
            hotel_repo = HotelRepository(conn_proxy)
            proxy = hotel_repo.get_random_proxy()
            if proxy:
                proxy_display = proxy.split("@")[-1] if "@" in proxy else proxy
                print(f"🔒 Proxy selected for entire execution: {proxy_display}")
            else:
                print("⚠️ No proxies found in database, will use direct connection")
                proxy = None
        finally:
            conn_proxy.close()
    except DatabaseConnectionError as e:
        logger.warning(f"Failed to get proxy: {e}, continuing without proxy")
        proxy = None

    # Calculate dates: from today to next configured days
    today = datetime.now()
    dates = []
    for i in range(days_to_extract):
        checkin_date = today + timedelta(days=i)
        checkout_date = checkin_date + timedelta(days=1)
        dates.append(
            {
                "checkin": checkin_date.strftime("%Y-%m-%d"),
                "checkout": checkout_date.strftime("%Y-%m-%d"),
            }
        )

    # Add weekend extractions
    start_date = today
    end_date = today + timedelta(days=days_to_extract - 1)
    weekend_extractions = detect_weekend_extractions(start_date, end_date)
    dates.extend(weekend_extractions)

    print(
        f"📅 Dates to process: {dates[0]['checkin']} to {dates[-1]['checkin']} "
        f"({len(dates)} days)"
    )
    if weekend_extractions:
        print(f"📅 Weekend extractions added: {len(weekend_extractions)}")
    print("=" * 80)

    # Global statistics
    total_stats = {
        "hotels_processed": 0,
        "total_sessions_created": 0,
        "total_sessions_updated": 0,
        "total_room_availabilities_created": 0,
        "total_errors": [],
    }

        # Process each hotel
    for hotel_idx, hotel in enumerate(hotels, 1):
        hotel_id = hotel.id
        hotel_name = hotel.name
        hotel_slug = hotel.slug or hotel.url.split("/")[-1].split(".")[0] if hotel.url else ""
        hotel_currency = hotel.currency or settings.booking_currency

        if not hotel.url:
            logger.warning(f"Hotel {hotel_id} has no URL, skipping...")
            continue

        print(f"\n🏨 [{hotel_idx}/{len(hotels)}] Processing hotel: {hotel_name} (ID: {hotel_id})")
        print("-" * 80)

        hotel_stats = {
            "sessions_created": 0,
            "sessions_updated": 0,
            "room_availabilities_created": 0,
            "errors": [],
        }

        # Process each date for this hotel
        for date_idx, date_info in enumerate(dates, 1):
            checkin = date_info["checkin"]
            checkout = date_info["checkout"]

            print(f"  📆 [{date_idx}/{len(dates)}] Date: {checkin} -> {checkout}")

            # Create new connection for each request
            conn = None
            try:
                conn = get_db_connection()
                service = UpdatePricesService(conn, proxy=proxy)

                # Build URL with all required parameters
                hotel_url = build_booking_url(
                    hotel_slug=hotel_slug,
                    checkin=checkin,
                    checkout=checkout,
                    currency=hotel_currency,
                    adults=1,
                    children=0,
                )

                # Perform scraping
                results = service.update_hotel_prices(
                    hotel_id=hotel_id,
                    hotel_url=hotel_url,
                    checkin_date=checkin,
                    checkout_date=checkout,
                    adults=1,
                    children=0,
                    currency=hotel_currency,
                    extraction_mode="daily",
                    proxy_id=None,
                )

                # Accumulate statistics
                hotel_stats["sessions_created"] += results.get("sessions_created", 0)
                hotel_stats["sessions_updated"] += results.get("sessions_updated", 0)
                hotel_stats["room_availabilities_created"] += results.get(
                    "room_availabilities_created", 0
                )

                if results.get("errors"):
                    hotel_stats["errors"].extend(results["errors"])

                print(
                    f"    ✅ Sessions: {results.get('sessions_created', 0)} created, "
                    f"{results.get('sessions_updated', 0)} updated | "
                    f"Rooms: {results.get('room_availabilities_created', 0)}"
                )

                if results.get("errors"):
                    print(f"    ⚠️  Errors: {len(results['errors'])}")
                    for error in results["errors"]:
                        logger.error(f"      - {error}")

            except Exception as e:
                error_msg = f"Error processing date {checkin} for hotel {hotel_id}: {str(e)}"
                logger.error(error_msg)
                hotel_stats["errors"].append(error_msg)
                print(f"    ❌ Error: {str(e)}")

            finally:
                # Close connection after each request
                if conn:
                    try:
                        conn.close()
                        logger.debug(f"Connection closed for date {checkin}")
                    except Exception as e:
                        logger.warning(f"Error closing connection: {e}")

            # Random delay between requests
            # Don't delay after last request of last hotel
            if not (hotel_idx == len(hotels) and date_idx == len(dates)):
                delay = random.randint(
                    settings.scraping_delay_min, settings.scraping_delay_max
                )
                print(f"    ⏳ Waiting {delay} seconds before next request...")
                time.sleep(delay)

        # Hotel summary
        print(f"\n  📊 Hotel summary {hotel_name}:")
        print(f"     - Sessions created: {hotel_stats['sessions_created']}")
        print(f"     - Sessions updated: {hotel_stats['sessions_updated']}")
        print(f"     - Rooms created: {hotel_stats['room_availabilities_created']}")
        print(f"     - Errors: {len(hotel_stats['errors'])}")

        # Accumulate in global statistics
        total_stats["hotels_processed"] += 1
        total_stats["total_sessions_created"] += hotel_stats["sessions_created"]
        total_stats["total_sessions_updated"] += hotel_stats["sessions_updated"]
        total_stats["total_room_availabilities_created"] += hotel_stats[
            "room_availabilities_created"
        ]
        total_stats["total_errors"].extend(hotel_stats["errors"])

    # Final summary
    print("\n" + "=" * 80)
    print("📈 FINAL SUMMARY")
    print("=" * 80)
    print(f"Hotels processed: {total_stats['hotels_processed']}")
    print(f"Total sessions created: {total_stats['total_sessions_created']}")
    print(f"Total sessions updated: {total_stats['total_sessions_updated']}")
    print(f"Total rooms created: {total_stats['total_room_availabilities_created']}")
    print(f"Total errors: {len(total_stats['total_errors'])}")

    if total_stats["total_errors"]:
        print("\n⚠️  Errors found:")
        for error in total_stats["total_errors"][:10]:
            print(f"  - {error}")
        if len(total_stats["total_errors"]) > 10:
            print(f"  ... and {len(total_stats['total_errors']) - 10} more errors")

    # Final cleanup of zombie processes and temp files
    logger.info("🧹 Final cleanup: removing Chrome/ChromeDriver zombie processes...")
    kill_chrome_processes()
    cleanup_old_temp_dirs(max_age_hours=1)

    print("\n✅ Process completed!")


if __name__ == "__main__":
    main()

