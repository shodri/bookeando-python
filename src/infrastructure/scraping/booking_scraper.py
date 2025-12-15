"""Booking.com scraper - infrastructure layer implementation."""

import logging
import time
from datetime import datetime
from typing import Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config.settings import settings
from src.domain.exceptions import ScrapingError, ScrapingNetworkError, ScrapingTimeoutError
from src.domain.models import RoomAvailability, ScrapedHotelData
from src.domain.services import PriceService, TextExtractionService
from src.infrastructure.scraping.driver_factory import DriverFactory

logger = logging.getLogger(__name__)


class BookingScraper:
    """Booking.com scraper - returns domain objects only."""

    def __init__(self, proxy: str | None = None) -> None:
        """Initialize the Booking scraper.

        Args:
            proxy: Optional proxy URL in format "http://ip_address:port".

        Raises:
            ScrapingError: If driver initialization fails.
        """
        self.proxy = proxy
        self.driver: webdriver.Chrome | None = None
        self.service = None
        self.temp_dir: str | None = None
        self.debug_port: int | None = None
        try:
            self.driver, self.temp_dir, self.debug_port = DriverFactory.create_driver(proxy=proxy)
        except Exception as e:
            logger.error(f"Error initializing driver: {e}")
            self.close()
            raise ScrapingError(f"Failed to initialize scraper: {e}") from e

    def scrape_hotel(
        self,
        hotel_url: str,
        checkin_date: str,
        checkout_date: str,
        adults: int = 1,
        children: int = 0,
        currency: str | None = None,
    ) -> ScrapedHotelData:
        """Scrape hotel data from Booking.com.

        Args:
            hotel_url: Hotel URL on Booking.com.
            checkin_date: Check-in date (YYYY-MM-DD).
            checkout_date: Check-out date (YYYY-MM-DD).
            adults: Number of adults.
            children: Number of children.
            currency: Currency code.

        Returns:
            ScrapedHotelData domain object.

        Raises:
            ScrapingNetworkError: If network error occurs.
            ScrapingTimeoutError: If operation times out.
            ScrapingError: For other scraping errors.
        """
        if not self.driver:
            raise ScrapingError("Driver not initialized")

        if currency is None:
            currency = settings.booking_currency

        capture_date = datetime.now()
        room_availabilities: list[RoomAvailability] = []

        try:
            logger.info(f"🌐 Navegando a: {hotel_url}")
            self.driver.get(hotel_url)

            # Esperar a que cargue la página
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            time.sleep(3)

            # Log del HTML para debugging
            html_length = len(self.driver.page_source)
            logger.info(f"[BookingScraper] HTML recibido - Longitud: {html_length} caracteres")

            # Esperar explícitamente a que la tabla de habitaciones aparezca
            # Intentar múltiples selectores para diferentes países/idiomas
            table_selectors = [
                "table.hprt-table",
                "table#hprt-table",
                "table[class*='hprt-table']",
            ]
            
            table_found = False
            for selector in table_selectors:
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    table_found = True
                    logger.info(f"[BookingScraper] Tabla encontrada con selector: {selector}")
                    break
                except Exception:
                    continue
            
            if not table_found:
                logger.warning("[BookingScraper] No se encontró la tabla de habitaciones")
            
            # Esperar un poco más para que se carguen las filas dinámicamente
            time.sleep(2)

            # Buscar tabla de habitaciones - intentar múltiples estrategias
            # Estrategia 1: Buscar en tbody (más específico)
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table.hprt-table tbody tr, table#hprt-table tbody tr")
            logger.info(f"[BookingScraper] Filas encontradas en tbody: {len(rows)}")
            
            # Estrategia 2: Si no encuentra con tbody, intentar sin tbody (fallback)
            if not rows:
                rows = self.driver.find_elements(By.CSS_SELECTOR, "table.hprt-table tr, table#hprt-table tr")
                logger.info(f"[BookingScraper] Filas encontradas sin tbody: {len(rows)}")
            
            # Estrategia 3: Buscar por data-block-id directamente
            if not rows:
                rows = self.driver.find_elements(By.CSS_SELECTOR, "tr[data-block-id]")
                logger.info(f"[BookingScraper] Filas encontradas por data-block-id: {len(rows)}")
            
            # Filtrar solo filas que tienen data-block-id (son filas de habitaciones reales)
            # Excluir filas del header
            filtered_rows = []
            for row in rows:
                row_class = row.get_attribute("class") or ""
                data_block_id = row.get_attribute("data-block-id")
                
                # Excluir headers explícitamente
                if "hprt-table-header" in row_class.lower():
                    continue
                
                # Incluir si tiene data-block-id O si es una fila js-rt-block-row
                if data_block_id or "js-rt-block-row" in row_class.lower():
                    filtered_rows.append(row)
                    logger.debug(f"[BookingScraper] Fila válida encontrada - data-block-id: {data_block_id}, class: {row_class}")
            
            rows = filtered_rows
            row_count = len(rows)
            logger.info(f"[BookingScraper] Filas válidas encontradas en tabla: {row_count}")
            
            if row_count == 0:
                logger.warning("[BookingScraper] ⚠️ No se encontraron filas de habitaciones. Verificando HTML...")
                # Intentar guardar HTML para debugging
                try:
                    page_source_sample = self.driver.page_source[:5000]  # Primeros 5000 caracteres
                    logger.debug(f"[BookingScraper] Muestra del HTML: {page_source_sample}")
                except Exception:
                    pass

            previous_room_name = ""
            previous_availability = ""  # Match original: start as empty string
            last_estudio_index = -1

            for index, row in enumerate(rows):
                try:
                    # Verificar que la fila no sea del header
                    row_class = row.get_attribute("class") or ""
                    
                    # Saltar solo si es explícitamente un header
                    if "hprt-table-header" in row_class.lower():
                        logger.debug(f"[BookingScraper] Saltando fila {index} - es header")
                        continue
                    
                    row_html = row.get_attribute("innerHTML")
                    
                    # Si la fila está vacía o no tiene contenido relevante, saltar
                    if not row_html or len(row_html.strip()) < 50:
                        logger.debug(f"[BookingScraper] Saltando fila {index} - contenido vacío o muy corto")
                        continue

                    # Non-refundable detection
                    if "no reembolsable" in row_html.lower():
                        logger.info(
                            f"[BookingScraper] No reembolsable | Hotel: {hotel_url} | "
                            f"Fecha: {checkin_date} | Fila: {index}"
                        )

                    # Room name
                    room_type_elements = row.find_elements(
                        By.CSS_SELECTOR, "span.hprt-roomtype-icon-link"
                    )
                    room_type = room_type_elements[0].text.strip() if room_type_elements else ""

                    # Si no tiene nombre, usar el de la iteración anterior
                    if not room_type:
                        room_type = previous_room_name
                    else:
                        previous_room_name = room_type

                    # Precio base (tachado)
                    base_price_elements = row.find_elements(
                        By.CSS_SELECTOR, "div.bui-f-color-destructive.js-strikethrough-price"
                    )
                    base_price = (
                        PriceService.clean_price(base_price_elements[0].text)
                        if base_price_elements
                        else 0.0
                    )

                    # Precio final
                    final_price_elements = row.find_elements(
                        By.CSS_SELECTOR, "span.prco-valign-middle-helper"
                    )
                    final_price = (
                        PriceService.clean_price(final_price_elements[0].text)
                        if final_price_elements
                        else 0.0
                    )

                    # Fallback para precio final
                    if not final_price:
                        final_price_elements = row.find_elements(
                            By.CSS_SELECTOR, "span.prc-no-css"
                        )
                        final_price = (
                            PriceService.clean_price(final_price_elements[0].text)
                            if final_price_elements
                            else 0.0
                        )

                    # Oferta
                    offer_elements = row.find_elements(
                        By.CSS_SELECTOR,
                        "div.c-deals-container > div > div:nth-child(2) > span > span > span",
                    )
                    offer = offer_elements[0].text.strip() if offer_elements else ""

                    # Disponibilidad
                    availability_elements = row.find_elements(
                        By.CSS_SELECTOR,
                        "li.bui-list__item.bui-text--color-destructive-dark div.bui-list__description",
                    )
                    availability = (
                        TextExtractionService.extract_number(availability_elements[0].text)
                        if availability_elements
                        else None
                    )

                    if availability is None:
                        availability_elements = row.find_elements(
                            By.CSS_SELECTOR, "span.only_x_left.urgency_message_red"
                        )
                        availability_text = (
                            availability_elements[0].text if availability_elements else ""
                        )
                        availability = TextExtractionService.extract_number(availability_text)

                    # Si no tiene disponibilidad, usar la de la iteración anterior
                    if availability is None:
                        availability = previous_availability if previous_availability else None
                    else:
                        previous_availability = availability

                    # Aplicar incremento del 10.5%
                    incremento = settings.price_increment_multiplier
                    if base_price > 0:
                        base_price = base_price * incremento
                        base_price = int(base_price)
                    if final_price > 0:
                        final_price = final_price * incremento
                        final_price = int(final_price)

                    # No reembolsable
                    no_reembolsable = "no reembolsable" in row_html.lower()

                    logger.info(
                        "[BookingScraper] Parser data dia a dia",
                        extra={
                            "roomType": room_type,
                            "basePrice": base_price,
                            "finalPrice": final_price,
                            "offer": offer,
                            "availability": availability,
                            "checkin": checkin_date,
                            "checkout": checkout_date,
                            "date_actual": checkin_date,
                        },
                    )

                    # Solo agregar si hay algún dato relevante
                    if room_type or final_price or base_price:
                        # Verificar si es una habitación "Estudio"
                        is_estudio = "estudio" in room_type.lower()

                        if is_estudio:
                            # Si ya teníamos un "Estudio" anterior, remover el anterior
                            if last_estudio_index >= 0:
                                if last_estudio_index < len(room_availabilities):
                                    removed_room = room_availabilities[last_estudio_index].room_type_name
                                    room_availabilities.pop(last_estudio_index)
                                    logger.info(
                                        f"[BookingScraper] Eliminando 'Estudio' anterior | "
                                        f"Hotel: {hotel_url} | Fecha: {checkin_date} | "
                                        f"Habitación: {removed_room}"
                                    )

                            # Guardar la posición de este "Estudio"
                            last_estudio_index = len(room_availabilities)

                        room_availability = RoomAvailability(
                            room_type_id=0,  # Will be set by repository
                            room_type_name=room_type,
                            base_price=base_price,
                            final_price=final_price,
                            availability=availability,
                            offer=offer if offer else None,
                            non_refundable=no_reembolsable,
                        )

                        room_availabilities.append(room_availability)

                        # Log cuando se detecta no reembolsable
                        if no_reembolsable:
                            logger.info(
                                f"[BookingScraper] Habitación no reembolsable detectada | "
                                f"Hotel: {hotel_url} | Fecha: {checkin_date} | Habitación: {room_type}"
                            )

                except Exception as e:
                    logger.error(f"Error processing row {index}: {e}")
                    continue

            logger.info(
                f"[BookingScraper] Data extracted - Total rooms: {len(room_availabilities)}"
            )

            return ScrapedHotelData(
                hotel_url=hotel_url,
                checkin_date=checkin_date,
                checkout_date=checkout_date,
                capture_date=capture_date,
                room_availabilities=room_availabilities,
                success=True,
                adults=adults,
                children=children,
                currency=currency,
            )

        except Exception as e:
            logger.error(f"General error in scrape_hotel: {e}")
            return ScrapedHotelData(
                hotel_url=hotel_url,
                checkin_date=checkin_date,
                checkout_date=checkout_date,
                capture_date=capture_date,
                room_availabilities=[],
                success=False,
                error_message=str(e),
                adults=adults,
                children=children,
                currency=currency,
            )

    def close(self) -> None:
        """Close the driver and clean up resources."""
        DriverFactory.cleanup_driver(self.driver, self.service, self.temp_dir)
        self.driver = None
        self.service = None
        self.temp_dir = None
        self.debug_port = None

    def __enter__(self) -> "BookingScraper":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

