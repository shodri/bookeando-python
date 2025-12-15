from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import re
import time
import json
import mysql.connector
from datetime import datetime, timedelta
import logging
import random
import argparse
import shutil
import tempfile
import subprocess
import os
import signal
import glob
from pathlib import Path

from src.config.settings import settings

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN DE PROXY
# ============================================================================
# NOTA: Ahora se usa la función get_random_proxy() que obtiene proxies aleatorios
# de la tabla 'proxies' en la base de datos. La constante PROXY ya no se utiliza.
# Si necesitas usar un proxy fijo, puedes modificar get_random_proxy() o usar
# la constante directamente en el código.
# ============================================================================


def fetch_hotels(limit=100):
    conn = mysql.connector.connect(**settings.db_connection_params)
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM hotels LIMIT %s", (limit,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def get_random_proxy():
    """
    Obtiene un proxy aleatorio de la tabla 'proxies' en la base de datos.

    Returns:
        str: URL del proxy en formato "http://ip_address:port" o None si no hay proxies disponibles
    """
    conn = mysql.connector.connect(**settings.db_connection_params)
    try:
        cur = conn.cursor(dictionary=True)
        # Obtener un proxy aleatorio de la tabla proxies
        cur.execute("SELECT ip_address, port FROM proxies ORDER BY RAND() LIMIT 1")
        row = cur.fetchone()

        if row and row.get('ip_address') and row.get('port'):
            ip_address = row['ip_address']
            port = row['port']
            proxy_url = f"http://{ip_address}:{port}"
            logger.info(f"🔒 Proxy aleatorio seleccionado: {proxy_url}")
            return proxy_url
        else:
            logger.warning("⚠️ No se encontraron proxies disponibles en la base de datos")
            return None
    except Exception as e:
        logger.error(f"❌ Error al obtener proxy de la base de datos: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def kill_chrome_processes():
    """Mata todos los procesos de Chrome y ChromeDriver que puedan estar colgados"""
    try:
        # Matar procesos de Chrome
        subprocess.run(['pkill', '-9', '-f', 'chrome.*--headless'], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        # Matar procesos de ChromeDriver
        subprocess.run(['pkill', '-9', '-f', 'chromedriver'], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        logger.info("Procesos Chrome/ChromeDriver zombies eliminados")
    except Exception as e:
        logger.warning(f"Error matando procesos Chrome: {e}")

def cleanup_old_temp_dirs(max_age_hours=24):
    """Limpia directorios temporales antiguos que puedan haber quedado"""
    try:
        temp_base = tempfile.gettempdir()
        pattern = os.path.join(temp_base, 'tmp*')
        
        cleaned = 0
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for temp_dir in glob.glob(pattern):
            try:
                # Verificar que sea un directorio y no el base
                if os.path.isdir(temp_dir) and temp_dir != temp_base:
                    # Verificar edad del directorio
                    dir_age = now - os.path.getmtime(temp_dir)
                    if dir_age > max_age_seconds:
                        # Verificar que sea un directorio temporal de Chrome (contiene user-data-dir)
                        if os.path.exists(os.path.join(temp_dir, 'Default')):
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            cleaned += 1
                            logger.debug(f"Directorio temporal antiguo eliminado: {temp_dir}")
            except Exception as e:
                logger.debug(f"Error verificando directorio {temp_dir}: {e}")
                continue
        
        if cleaned > 0:
            logger.info(f"Limpieza de directorios temporales: {cleaned} directorios eliminados")
    except Exception as e:
        logger.warning(f"Error limpiando directorios temporales antiguos: {e}")

class BookingScraper:
    def __init__(self, proxy=None):
        """
        Inicializa el scraper de Booking

        Args:
            proxy: URL del proxy en formato "http://usuario:contraseña@host:puerto" o None
        """
        self.proxy = proxy
        self.driver = None
        self.service = None
        self.temp_dir = None
        self.debug_port = None
        try:
            self.setup_driver()
        except Exception as e:
            logger.error(f"Error inicializando driver: {e}")
            # Asegurar limpieza si falla la inicialización
            self.close()
            raise

    def setup_driver(self):
        """Configurar el driver de Chrome con soporte para proxy"""
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # 🔥 AGREGAR ESTAS OPCIONES ESENCIALES PARA SERVIDORES
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        # Usar puerto dinámico para evitar conflictos entre múltiples instancias
        import socket
        sock = socket.socket()
        sock.bind(('', 0))
        self.debug_port = sock.getsockname()[1]
        sock.close()
        options.add_argument(f"--remote-debugging-port={self.debug_port}")

        # 🔥 USAR DIRECTORIO TEMPORAL ÚNICO PARA CADA INSTANCIA
        self.temp_dir = tempfile.mkdtemp()
        options.add_argument(f"--user-data-dir={self.temp_dir}")

        # 🔥 MODO HEADLESS (configurable desde .env)
        if settings.headless_mode:
            options.add_argument("--headless=new")
            logger.info("🔒 Modo headless activado")
        else:
            logger.info("👁️ Modo headless desactivado - se mostrará el navegador")

        # Configurar proxy si está disponible
        if self.proxy:
            # Extraer IP:PORT del string del proxy
            proxy_server = self.proxy.replace('http://', '').replace('https://', '').split('@')[-1]
            options.add_argument(f'--proxy-server={proxy_server}')
            logger.info(f"🔒 Configurando proxy: {proxy_server}")

        self.service = None
        try:
            self.service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=self.service, options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            logger.error(f"Error creando driver de Chrome: {e}")
            # Limpiar directorio temporal si falla la inicialización
            if self.temp_dir:
                try:
                    shutil.rmtree(self.temp_dir, ignore_errors=True)
                    self.temp_dir = None
                except Exception as cleanup_error:
                    logger.warning(f"Error limpiando directorio temporal: {cleanup_error}")
            self.service = None
            raise

    def clean_price(self, price_text):
        """Limpiar y convertir precio a float"""
        if not price_text:
            return 0.0

        # Remover símbolos de moneda y separadores de miles
        clean = re.sub(r'[^\d,]', '', price_text)
        clean = clean.replace(',', '.')

        try:
            return float(clean)
        except ValueError:
            return 0.0

    def extract_number(self, text):
        """Extraer número de un texto"""
        if not text:
            return None

        match = re.search(r'\d+', text)
        return int(match.group()) if match else None

    def parse_hotel_data(self, hotel_url, params, conn=None, hotel_id=None, proxy_id=None):
        """Extraer datos de habitaciones del hotel.

        Opcional: si se pasan `conn` (mysql connector) y `hotel_id`, la función
        intentará crear/actualizar una entrada en `scrape_sessions` y guardar
        las `room_availabilities` usando las funciones auxiliares definidas
        en otras celdas (`create_scrape_session`, `process_room_availabilities`).
        """
        capture_date = datetime.now().isoformat()
        date = params.get('checkin', '')
        room_types_data = []

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

            # Buscar tabla de habitaciones
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table.hprt-table tr")
            row_count = len(rows)
            logger.info(f"[BookingScraper] Filas encontradas en tabla: {row_count}")

            previous_room_name = ''
            previous_availability = ''
            last_estudio_index = -1

            for index, row in enumerate(rows):
                try:
                    row_html = row.get_attribute('innerHTML')

                    # No reembolsable
                    if 'no reembolsable' in row_html.lower():
                        logger.info(f"[BookingScraper] No reembolsable | Hotel: {hotel_url} | Fecha: {params.get('checkin')} | Fila: {index}")

                    # Nombre de habitación
                    room_type_elements = row.find_elements(By.CSS_SELECTOR, "span.hprt-roomtype-icon-link")
                    room_type = room_type_elements[0].text.strip() if room_type_elements else ''

                    # Si no tiene nombre, usar el de la iteración anterior
                    if not room_type:
                        room_type = previous_room_name
                    else:
                        previous_room_name = room_type

                    # Precio base (tachado)
                    base_price_elements = row.find_elements(By.CSS_SELECTOR, "div.bui-f-color-destructive.js-strikethrough-price")
                    base_price = self.clean_price(base_price_elements[0].text) if base_price_elements else 0.0

                    # Precio final
                    final_price_elements = row.find_elements(By.CSS_SELECTOR, "span.prco-valign-middle-helper")
                    final_price = self.clean_price(final_price_elements[0].text) if final_price_elements else 0.0

                    # Fallback para precio final
                    if not final_price:
                        final_price_elements = row.find_elements(By.CSS_SELECTOR, "span.prc-no-css")
                        final_price = self.clean_price(final_price_elements[0].text) if final_price_elements else 0.0

                    # Oferta
                    offer_elements = row.find_elements(By.CSS_SELECTOR, "div.c-deals-container > div > div:nth-child(2) > span > span > span")
                    offer = offer_elements[0].text.strip() if offer_elements else ''

                    # Disponibilidad
                    availability_elements = row.find_elements(By.CSS_SELECTOR, "li.bui-list__item.bui-text--color-destructive-dark div.bui-list__description")
                    availability = self.extract_number(availability_elements[0].text) if availability_elements else None

                    if availability is None:
                        availability_elements = row.find_elements(By.CSS_SELECTOR, "span.only_x_left.urgency_message_red")
                        availability_text = availability_elements[0].text if availability_elements else ''
                        availability = self.extract_number(availability_text)

                    # Si no tiene disponibilidad, usar la de la iteración anterior
                    if availability is None:
                        availability = previous_availability if previous_availability else None
                    else:
                        previous_availability = availability

                    # Aplicar incremento del 10.5%
                    incremento = 1.105
                    if base_price > 0:
                        base_price = base_price * incremento
                        base_price = int(base_price)
                    if final_price > 0:
                        final_price = final_price * incremento
                        final_price = int(final_price)

                    # No reembolsable
                    no_reembolsable = 'no reembolsable' in row_html.lower()

                    logger.info('[BookingScraper] Parser data dia a dia', extra={
                        'roomType': room_type,
                        'basePrice': base_price,
                        'finalPrice': final_price,
                        'offer': offer,
                        'availability': availability,
                        'checkin': params.get('checkin'),
                        'checkout': params.get('checkout'),
                        'date_actual': params.get('checkin'),
                    })

                    # Solo agregar si hay algún dato relevante
                    if room_type or final_price or base_price:
                        # Verificar si es una habitación "Estudio"
                        is_estudio = 'estudio' in room_type.lower()

                        if is_estudio:
                            # Si ya teníamos un "Estudio" anterior, remover el anterior
                            if last_estudio_index >= 0:
                                if last_estudio_index < len(room_types_data):
                                    removed_room = room_types_data[last_estudio_index]['name']
                                    room_types_data.pop(last_estudio_index)
                                    logger.info(f"[BookingScraper] Eliminando 'Estudio' anterior | Hotel: {hotel_url} | Fecha: {params.get('checkin')} | Habitación: {removed_room}")

                            # Guardar la posición de este "Estudio"
                            last_estudio_index = len(room_types_data)

                        room_data = {
                            'name': room_type,
                            'base_price': base_price,
                            'final_price': final_price,
                            'offer': offer,
                            'availability': availability,
                            'non_refundable': no_reembolsable,
                        }

                        room_types_data.append(room_data)

                        # Log cuando se detecta no reembolsable
                        if no_reembolsable:
                            logger.info(f"[BookingScraper] Habitación no reembolsable detectada | Hotel: {hotel_url} | Fecha: {params.get('checkin')} | Habitación: {room_type}")

                except Exception as e:
                    logger.error(f"Error procesando fila {index}: {e}")
                    continue

            logger.info(f"[BookingScraper] Datos extraídos - Total habitaciones: {len(room_types_data)}")

            # Estructura final organizada
            result = {
                'date': date,
                'capture_date': capture_date,
                'hotel': hotel_url,
                'checkin_date': params.get('checkin'),
                'checkout_date': params.get('checkout'),
                'adults': params.get('adults', 1),
                'children': params.get('children', 0),
                'currency': params.get('currency', 'ARS'),
                'room_types': room_types_data,
                'success': True
            }

            return result

        except Exception as e:
            logger.error(f"Error general en parse_hotel_data: {e}")
            return None

    def _kill_chrome_processes_by_temp_dir(self):
        """Mata procesos de Chrome relacionados con nuestro directorio temporal"""
        if not self.temp_dir:
            return
        
        try:
            # Buscar procesos que estén usando nuestro directorio temporal
            result = subprocess.run(
                ['pgrep', '-f', f'--user-data-dir={self.temp_dir}'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        pid_int = int(pid.strip())
                        os.kill(pid_int, signal.SIGKILL)
                        logger.debug(f"Proceso Chrome matado (PID: {pid_int})")
                    except (ValueError, ProcessLookupError, PermissionError):
                        pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        except Exception as e:
            logger.debug(f"Error matando procesos por temp_dir: {e}")

    def close(self):
        """Cerrar el driver y limpiar recursos de forma agresiva"""
        # Guardar referencia al temp_dir antes de limpiar
        temp_dir_to_clean = getattr(self, 'temp_dir', None)
        
        # Cerrar el service primero si existe
        if hasattr(self, 'service') and self.service is not None:
            try:
                if hasattr(self.service, 'process') and self.service.process:
                    try:
                        self.service.process.terminate()
                        self.service.process.wait(timeout=3)
                    except (subprocess.TimeoutExpired, AttributeError):
                        try:
                            self.service.process.kill()
                        except (AttributeError, ProcessLookupError):
                            pass
            except Exception as e:
                logger.debug(f"Error cerrando service: {e}")
            finally:
                self.service = None

        # Cerrar el driver de forma segura
        if hasattr(self, 'driver') and self.driver is not None:
            try:
                # Intentar quit() primero (cierra todos los procesos relacionados)
                self.driver.quit()
                logger.debug("Driver cerrado exitosamente con quit()")
            except Exception as e:
                logger.warning(f"Error al cerrar driver con quit(): {e}, intentando close()...")
                try:
                    # Fallback: intentar close() (cierra solo la ventana actual)
                    self.driver.close()
                    logger.debug("Driver cerrado exitosamente con close()")
                except Exception as e2:
                    logger.debug(f"Error al cerrar driver con close(): {e2}")
            
            # Matar procesos relacionados con nuestro directorio temporal
            self._kill_chrome_processes_by_temp_dir()
            
            # Asegurar que el driver sea None
            self.driver = None

        # Limpiar directorio temporal de forma agresiva
        if temp_dir_to_clean and os.path.exists(temp_dir_to_clean):
            try:
                # Matar cualquier proceso que aún esté usando el directorio
                self._kill_chrome_processes_by_temp_dir()
                
                # Intentar eliminar el directorio
                shutil.rmtree(temp_dir_to_clean, ignore_errors=True)
                logger.debug(f"Directorio temporal limpiado: {temp_dir_to_clean}")
            except Exception as e:
                logger.warning(f"Error al limpiar directorio temporal {temp_dir_to_clean}: {e}")
            finally:
                self.temp_dir = None
        elif hasattr(self, 'temp_dir'):
            self.temp_dir = None
        
        # Limpiar referencia al puerto de debugging
        if hasattr(self, 'debug_port'):
            self.debug_port = None

    def __del__(self):
        """Destructor: asegura la limpieza de recursos si close() no se llama explícitamente"""
        try:
            self.close()
        except Exception:
            # Ignorar excepciones durante la destrucción para evitar errores en el GC
            pass

# Función de uso sencillo
def scrape_booking_hotel(hotel_url, checkin, checkout, adults=2, children=0, conn=None, hotel_id=None, proxy=None):
    """Función simple para scrapear un hotel y opcionalmente guardar en BD"""
    scraper = BookingScraper(proxy=proxy)
    try:
        params = {
            'checkin': checkin,
            'checkout': checkout,
            'adults': adults,
            'children': children,
            'currency': 'EUR'
        }

        result = scraper.parse_hotel_data(hotel_url, params, conn=conn, hotel_id=hotel_id)
        return result

    finally:
        scraper.close()



class HotelScrapingService:
    """Servicio para manejar el scraping de hoteles, similar a HotelScrapingService.php"""

    def __init__(self, conn, proxy=None):
        """
        Inicializa el servicio de scraping

        Args:
            conn: Conexión MySQL
            proxy: URL del proxy en formato "http://usuario:contraseña@host:puerto" o None
        """
        self.conn = conn
        self.proxy = proxy
        self.scraper = None

    def scrape_hotel(self, hotel_id, hotel_url, scraping_params, proxy_id=None):
        """Ejecuta el scraping de un hotel con los parámetros dados"""
        try:
            logger.info(f"Iniciando scraping para hotel {hotel_id} - Inicio {scraping_params.get('checkin_date')} a {scraping_params.get('checkout_date')}")

            # Verificar si es un reintento de una fecha específica
            is_retry_mode = scraping_params.get('retry_mode', False)
            retry_date = scraping_params.get('retry_date')

            if is_retry_mode and retry_date:
                logger.info(f"Modo reintento activado para fecha: {retry_date}")
                return self._retry_specific_date(hotel_id, hotel_url, scraping_params, retry_date, proxy_id)

            # Modo normal - procesar todas las fechas
            params = self._build_scraping_params(hotel_url, scraping_params)

            # Crear scraper y ejecutar
            self.scraper = BookingScraper(proxy=self.proxy)
            try:
                scraped_data = self.scraper.parse_hotel_data(
                    hotel_url,
                    params,
                    conn=None,
                    hotel_id=None,
                    proxy_id=proxy_id
                )

                # Convertir a formato esperado (similar al PHP)
                # El PHP espera un dict con hotel_slug como key y lista de resultados diarios
                hotel_slug = hotel_url.split('/')[-1].split('.')[0] if '/' in hotel_url else 'unknown'
                formatted_data = {hotel_slug: [scraped_data]} if scraped_data else {hotel_slug: []}

                return self._process_scraped_data(hotel_id, formatted_data, scraping_params, proxy_id)
            finally:
                if self.scraper:
                    self.scraper.close()
                    self.scraper = None

        except Exception as e:
            logger.error(f"Error scraping hotel {hotel_id}: {e}")
            raise

    def _retry_specific_date(self, hotel_id, hotel_url, scraping_params, retry_date, proxy_id):
        """Reintenta el scraping de una fecha específica"""
        logger.info(f"[HotelScrapingService] Reintentando scraping para hotel {hotel_id} - Fecha específica: {retry_date}")

        retry_params = {
            'checkin': retry_date,
            'checkout': (datetime.strptime(retry_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d'),
            'adults': 1,
            'children': 0,
            'currency': scraping_params.get('currency', 'EUR'),
            'extraction_mode': 'daily'
        }

        self.scraper = BookingScraper(proxy=self.proxy)
        try:
            scraped_data = self.scraper.parse_hotel_data(hotel_url, retry_params, conn=None, hotel_id=None, proxy_id=proxy_id)
            hotel_slug = hotel_url.split('/')[-1].split('.')[0] if '/' in hotel_url else 'unknown'
            formatted_data = {hotel_slug: [scraped_data]} if scraped_data else {hotel_slug: []}
            return self._process_scraped_data(hotel_id, formatted_data, scraping_params, proxy_id)
        finally:
            if self.scraper:
                self.scraper.close()
                self.scraper = None

    def _build_scraping_params(self, hotel_url, scraping_params):
        """Construye los parámetros para el scraper"""
        checkin = scraping_params.get('checkin_date') or scraping_params.get('checkin')
        checkout = scraping_params.get('checkout_date') or scraping_params.get('checkout')

        if not checkin or not checkout:
            raise ValueError('Faltan parámetros de fecha: checkin_date/checkin y checkout_date/checkout')

        return {
            'checkin': checkin,
            'checkout': checkout,
            'adults': 1,
            'children': 0,
            'currency': scraping_params.get('currency', 'EUR'),
            'extraction_mode': scraping_params.get('extraction_mode', 'daily')
        }

    def _process_scraped_data(self, hotel_id, scraped_data, scraping_params, proxy_id=None):
        """Procesa los datos extraídos y los guarda en la base de datos"""
        results = {
            'sessions_created': 0,
            'sessions_updated': 0,
            'room_availabilities_created': 0,
            'room_availabilities_deleted': 0,
            'errors': []
        }

        extraction_mode = scraping_params.get('extraction_mode', 'daily')

        for hotel_slug, daily_results in scraped_data.items():
            # Para modo 'restriction', solo crear una sesión con el rango completo
            if extraction_mode == 'restriction':
                if daily_results:
                    first_day_data = daily_results[0]
                    # Forzar que use las fechas del rango completo
                    first_day_data['checkin_date'] = scraping_params['checkin_date']
                    first_day_data['checkout_date'] = scraping_params['checkout_date']

                    try:
                        session_result = self._create_scrape_session(hotel_id, first_day_data, scraping_params, proxy_id)

                        if session_result['session_id']:
                            if session_result.get('updated'):
                                results['sessions_updated'] += 1
                            else:
                                results['sessions_created'] += 1

                        # Procesar todas las disponibilidades de todos los días en una sola sesión
                        if session_result['session_id']:
                            for day_data in daily_results:
                                availability_result = self._process_room_availabilities(
                                    hotel_id, day_data, session_result['session_id'], scraping_params
                                )
                                results['room_availabilities_created'] += availability_result['created']
                                results['room_availabilities_deleted'] += availability_result.get('deleted', 0)

                                if availability_result.get('errors'):
                                    results['errors'].extend(availability_result['errors'])
                    except Exception as e:
                        results['errors'].append(f'Error processing restriction data: {str(e)}')
                        logger.error(f"Error processing restriction data for hotel {hotel_id}: {e}")
            else:
                # Modo 'daily' - procesar cada día por separado
                for day_data in daily_results:
                    try:
                        session_result = self._create_scrape_session(hotel_id, day_data, scraping_params, proxy_id)

                        if session_result['session_id']:
                            if session_result.get('updated'):
                                results['sessions_updated'] += 1
                            else:
                                results['sessions_created'] += 1

                        if session_result['session_id']:
                            availability_result = self._process_room_availabilities(
                                hotel_id, day_data, session_result['session_id'], scraping_params
                            )
                            results['room_availabilities_created'] += availability_result['created']
                            results['room_availabilities_deleted'] += availability_result.get('deleted', 0)

                            if availability_result.get('errors'):
                                results['errors'].extend(availability_result['errors'])
                    except Exception as e:
                        results['errors'].append(f'Error processing day data: {str(e)}')
                        logger.error(f"Error processing day data for hotel {hotel_id}: {e}")

        return results

    def _create_scrape_session(self, hotel_id, day_data, scraping_params, proxy_id=None):
        """Crea una sesión de scraping"""
        response_status = day_data.get('response_status')
        checkin_date = day_data.get('checkin_date') or scraping_params.get('checkin_date')
        checkout_date = day_data.get('checkout_date') or scraping_params.get('checkout_date')
        url_requested = day_data.get('url_requested') or day_data.get('hotel')

        # Determinar search_type
        search_type = self._determine_search_type(
            scraping_params.get('extraction_mode', 'daily'),
            checkin_date,
            checkout_date
        )

        # Log para debugging
        checkin = datetime.strptime(checkin_date, '%Y-%m-%d')
        checkout = datetime.strptime(checkout_date, '%Y-%m-%d')
        days_difference = (checkout - checkin).days
        logger.info(f"[HotelScrapingService] Determined search_type: {search_type} | Mode: {scraping_params.get('extraction_mode')} | Checkin: {checkin_date} | Checkout: {checkout_date} | Days difference: {days_difference}")

        # Verificar si el response_status es 202 y no guardar la sesión
        if response_status == 202:
            logger.warning(f"No se guardó la sesión de scraping para hotel {hotel_id} - response_status es 202")
            return {'session_id': None, 'updated': False}

        cur = self.conn.cursor()
        try:
            # Buscar sesión existente
            cur.execute(
                "SELECT id FROM scrape_sessions WHERE hotel_id=%s AND checkin_date=%s AND checkout_date=%s LIMIT 1",
                (hotel_id, checkin_date, checkout_date)
            )
            row = cur.fetchone()

            capture_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            request_params = json.dumps(scraping_params, ensure_ascii=False)
            error_message = day_data.get('error_message')
            success = 1 if day_data.get('success', False) else 0
            adults = day_data.get('adults', scraping_params.get('adults', 1))
            children = day_data.get('children', scraping_params.get('children', 0))
            currency = day_data.get('currency', scraping_params.get('currency', 'EUR'))
            notes = day_data.get('restriction_message')
            execution_time = day_data.get('execution_time')
            room_types_found = len(day_data.get('room_types', []))
            has_restriction = day_data.get('has_restriction', False)

            if row:
                # Actualizar sesión existente
                sid = row[0]
                # Usar campos básicos que sabemos que existen
                cur.execute(
                    """UPDATE scrape_sessions SET
                        proxy_id=%s, capture_date=%s, adults=%s, children=%s, currency=%s,
                        url_requested=%s, response_status=%s, request_params=%s, error_message=%s,
                        success=%s, notes=%s, updated_at=%s
                        WHERE id=%s""",
                    (proxy_id, capture_date, adults, children, currency, url_requested,
                     response_status, request_params, error_message, success, notes,
                     capture_date, sid)
                )

                # Intentar actualizar campos adicionales si existen (con manejo de errores)
                try:
                    if 'extraction_batch_id' in scraping_params:
                        cur.execute(
                            "UPDATE scrape_sessions SET extraction_batch_id=%s WHERE id=%s",
                            (scraping_params['extraction_batch_id'], sid)
                        )
                except Exception:
                    pass  # Campo puede no existir

                try:
                    cur.execute(
                        "UPDATE scrape_sessions SET room_types_found=%s, search_type=%s, has_restriction=%s WHERE id=%s",
                        (room_types_found, search_type, has_restriction, sid)
                    )
                except Exception:
                    pass  # Campos pueden no existir

                self.conn.commit()

                logger.info(f"Se actualizó sesión existente de scraping para hotel {hotel_id} - re-extracción para fechas {checkin_date} a {checkout_date}")
                return {'session_id': sid, 'updated': True}
            else:
                # Crear nueva sesión - usar campos básicos primero
                base_fields = (
                    hotel_id, proxy_id, checkin_date, checkout_date, adults, children, currency,
                    capture_date, url_requested, response_status, request_params, error_message,
                    success, notes, capture_date, capture_date
                )

                # Intentar INSERT con campos básicos
                try:
                    cur.execute(
                        """INSERT INTO scrape_sessions
                            (hotel_id, proxy_id, checkin_date, checkout_date, adults, children, currency,
                             capture_date, url_requested, response_status, request_params, error_message,
                             success, notes, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        base_fields
                    )
                    new_id = cur.lastrowid

                    # Intentar actualizar campos adicionales si existen
                    if 'extraction_batch_id' in scraping_params:
                        try:
                            cur.execute(
                                "UPDATE scrape_sessions SET extraction_batch_id=%s WHERE id=%s",
                                (scraping_params['extraction_batch_id'], new_id)
                            )
                        except Exception:
                            pass

                    try:
                        cur.execute(
                            "UPDATE scrape_sessions SET room_types_found=%s, search_type=%s, has_restriction=%s WHERE id=%s",
                            (room_types_found, search_type, has_restriction, new_id)
                        )
                    except Exception:
                        pass

                    self.conn.commit()

                    logger.info(f"Se creó scrape_session id={new_id} hotel_id={hotel_id} ({checkin_date} -> {checkout_date})")
                    return {'session_id': new_id, 'updated': False}
                except Exception as e:
                    self.conn.rollback()
                    raise
        finally:
            cur.close()

    def _process_room_availabilities(self, hotel_id, day_data, scrape_session_id, scraping_params):
        """Procesa las disponibilidades de habitaciones"""
        results = {
            'created': 0,
            'deleted': 0,
            'errors': []
        }

        try:
            # Calcular las fechas para la eliminación (aunque no se eliminen, se mantiene la estructura)
            date_fields = self._calculate_date_fields(day_data, scraping_params)

            # Crear las nuevas room availabilities
            room_types = day_data.get('room_types', [])
            for room_type_data in room_types:
                try:
                    room_type_id = self._find_or_create_room_type(hotel_id, room_type_data)
                    if not room_type_id:
                        results['errors'].append(f"No se pudo crear/obtener room_type_id for {room_type_data.get('name')}")
                        continue

                    self._create_room_availability(
                        hotel_id, room_type_id, room_type_data, scrape_session_id, date_fields
                    )
                    results['created'] += 1
                except Exception as e:
                    results['errors'].append(f"Error processing room type {room_type_data.get('name')}: {str(e)}")
                    logger.error(f"Error processing room type for hotel {hotel_id}: {e}")

            logger.info(f"[HotelScrapingService] Creadas {results['created']} nuevas room availabilities para hotel {hotel_id}")
        except Exception as e:
            results['errors'].append(f'Error en processRoomAvailabilities: {str(e)}')
            logger.error(f"Error en processRoomAvailabilities para hotel {hotel_id}: {e}")

        return results

    def _find_or_create_room_type(self, hotel_id, room_type_data):
        """Encuentra o crea un tipo de habitación"""
        name = room_type_data.get('name', '').strip()
        if not name:
            return None

        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT id FROM room_types WHERE hotel_id=%s AND LOWER(name)=LOWER(%s) LIMIT 1",
                (hotel_id, name)
            )
            row = cur.fetchone()

            if row:
                return row[0]

            # Crear nuevo room_type
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                "INSERT INTO room_types (hotel_id, name, description, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)",
                (hotel_id, name, room_type_data.get('description', ''), now, now)
            )
            self.conn.commit()
            return cur.lastrowid
        finally:
            cur.close()

    def _calculate_date_fields(self, day_data, scraping_params):
        """Calcula los campos de fecha según el modo de extracción"""
        extraction_mode = scraping_params.get('extraction_mode', 'daily')

        if extraction_mode == 'daily':
            date_value = day_data.get('date') or scraping_params.get('checkin_date')
            date_start = date_value
            date_end = (datetime.strptime(date_start, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            date_start = scraping_params.get('checkin_date')
            date_end = scraping_params.get('checkout_date')
            date_value = None

        return {
            'date': date_value,
            'date_start': date_start,
            'date_end': date_end
        }

    def _create_room_availability(self, hotel_id, room_type_id, room_type_data, scrape_session_id, date_fields):
        """Crea una nueva disponibilidad de habitación"""
        non_refundable = 1 if room_type_data.get('non_refundable', False) else 0

        try:
            logger.info(f"[HotelScrapingService] Creando room availability | Hotel: {hotel_id} | Habitación: {room_type_data.get('name')} | Inicio: {date_fields['date_start']} | Fin: {date_fields['date_end']}")

            availability = self._format_availability(room_type_data.get('availability'))
            base_price = self._format_price(room_type_data.get('base_price'))
            final_price = self._format_price(room_type_data.get('final_price'))
            offer = room_type_data.get('offer') or None

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur = self.conn.cursor()
            try:
                cur.execute(
                    "INSERT INTO room_availabilities (scrape_session_id, room_type_id, room_available_count, offer, base_price, final_price, non_refundable, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (scrape_session_id, room_type_id, availability, offer, base_price, final_price, non_refundable, now, now)
                )
                self.conn.commit()

                logger.info(f'[HotelScrapingService] ✅ SUCCESS - RoomAvailability creado para hotel {hotel_id}')
            finally:
                cur.close()
        except Exception as e:
            logger.error(f'[HotelScrapingService] ❌ ERROR creando RoomAvailability: {e}')
            raise

    def _determine_search_type(self, extraction_mode, checkin_date, checkout_date):
        """Determina el tipo de búsqueda según el modo de extracción y la diferencia real de días"""
        if extraction_mode == 'daily':
            return 'single'

        checkin = datetime.strptime(checkin_date, '%Y-%m-%d')
        checkout = datetime.strptime(checkout_date, '%Y-%m-%d')
        days_difference = (checkout - checkin).days

        return 'multiple' if days_difference > 1 else 'single'

    def _format_price(self, price):
        """Formatea el precio para guardarlo en la base de datos"""
        return price if price else None

    def _format_availability(self, availability):
        """Formatea la disponibilidad para guardarlo en la base de datos"""
        if availability is None or availability == '' or (isinstance(availability, str) and not availability.strip()):
            return None

        try:
            return int(availability)
        except (ValueError, TypeError):
            return None



# Funciones auxiliares para compatibilidad (deprecated - usar HotelScrapingService)
def create_room_availabilities(conn=None, scrape_session_id=None, day_data=None, hotel_id=None):
    """DEPRECATED: Usar HotelScrapingService._process_room_availabilities en su lugar"""
    if day_data is None:
        raise ValueError('day_data is required')
    if scrape_session_id is None:
        raise ValueError('scrape_session_id is required')
    if conn is None:
        raise RuntimeError('No DB connection available.')

    service = HotelScrapingService(conn)
    return service._process_room_availabilities(hotel_id, day_data, scrape_session_id, {})


def get_room_type_id(conn=None, hotel_id=None, room_name=None):
    """Devuelve el `room_type.id` para `hotel_id` y `room_name` buscando en `room_types`.

    - Si `conn` es None, se intenta usar la variable global `conn`.
    - Devuelve `int` o `None` si no existe.
    """
    if room_name is None:
        raise ValueError('room_name es requerido')
    if hotel_id is None:
        raise ValueError('hotel_id es requerido')
    if conn is None:
        conn = globals().get('conn')
    if conn is None:
        raise RuntimeError('No hay conexión a BD disponible. Pasa `conn` o crea una variable global `conn`.')
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM room_types WHERE hotel_id=%s AND LOWER(name)=LOWER(%s) LIMIT 1", (hotel_id, room_name))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        cur.close()


def find_or_create_room_type_id(conn, hotel_id, room_name):
    """Buscar o crear room_type y devolver su ID."""
    if not room_name:
        return None

    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM room_types WHERE hotel_id=%s AND LOWER(name)=LOWER(%s) LIMIT 1", (hotel_id, room_name))
        row = cur.fetchone()
        if row:
            return row[0]
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("INSERT INTO room_types (hotel_id, name, created_at, updated_at) VALUES (%s,%s,%s,%s)",
                   (hotel_id, room_name, now, now))
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()







################################################ Ejemplo de uso ################################################

def detect_weekend_extractions(start_date, end_date):
    """
    Detecta fines de semana en el rango de fechas y retorna extracciones adicionales.

    Args:
        start_date: datetime - Fecha de inicio del rango
        end_date: datetime - Fecha de fin del rango

    Returns:
        Lista de diccionarios con formato {'checkin': 'YYYY-MM-DD', 'checkout': 'YYYY-MM-DD'}
        - Check-in viernes → Check-out domingo (2 días)
        - Check-in sábado → Check-out lunes (2 días)
    """
    weekend_extractions = []
    current_date = start_date

    # Iterar sobre el rango de fechas
    while current_date <= end_date:
        weekday = current_date.weekday()  # 0=lunes, 4=viernes, 5=sábado, 6=domingo

        # Detectar viernes (weekday == 4)
        if weekday == 4:  # Viernes
            checkout_date = current_date + timedelta(days=2)  # Domingo
            # Solo agregar si el check-in está dentro del rango
            if current_date <= end_date:
                weekend_extractions.append({
                    'checkin': current_date.strftime('%Y-%m-%d'),
                    'checkout': checkout_date.strftime('%Y-%m-%d')
                })

        # Detectar sábado (weekday == 5)
        elif weekday == 5:  # Sábado
            checkout_date = current_date + timedelta(days=2)  # Lunes
            # Solo agregar si el check-in está dentro del rango
            if current_date <= end_date:
                weekend_extractions.append({
                    'checkin': current_date.strftime('%Y-%m-%d'),
                    'checkout': checkout_date.strftime('%Y-%m-%d')
                })

        current_date += timedelta(days=1)

    return weekend_extractions

def get_db_connection():
    """Crea una nueva conexión a la base de datos"""
    return mysql.connector.connect(**settings.db_connection_params)

if __name__ == "__main__":
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Booking Scraper')
    parser.add_argument('--days', type=int, default=15, help='Cantidad de días a extraer (default: 15)')
    args = parser.parse_args()

    # Limpiar procesos zombies y archivos temporales antiguos al inicio
    logger.info("🧹 Limpiando procesos Chrome/ChromeDriver zombies y archivos temporales antiguos...")
    kill_chrome_processes()
    cleanup_old_temp_dirs(max_age_hours=1)  # Limpiar archivos de más de 1 hora
    logger.info("✅ Limpieza inicial completada")

    days_to_extract = args.days
    print(f"📅 Configurado para extraer {days_to_extract} días")

    # Obtener lista de hoteles (conexión temporal solo para esto)
    conn_temp = get_db_connection()
    try:
        cur_temp = conn_temp.cursor(dictionary=True)
        cur_temp.execute("SELECT * FROM hotels")
        hotels = cur_temp.fetchall()

        if not hotels:
            raise RuntimeError('No se encontraron hoteles en la tabla hotels')

        print(f"📋 Total de hoteles a procesar: {len(hotels)}")
    finally:
        cur_temp.close()
        conn_temp.close()

    # Seleccionar proxy una vez para toda la ejecución
    proxy = get_random_proxy()
    if proxy:
        proxy_display = proxy.replace('http://', '').replace('https://', '')
        print(f"🔒 Proxy seleccionado para toda la ejecución: {proxy_display}")
    else:
        print("⚠️ No se encontraron proxies en la base de datos, se usará conexión directa")

    # Calcular fechas: desde hoy hasta los próximos días configurados
    today = datetime.now()
    dates = []
    for i in range(days_to_extract):
        checkin_date = today + timedelta(days=i)
        checkout_date = checkin_date + timedelta(days=1)
        dates.append({
            'checkin': checkin_date.strftime('%Y-%m-%d'),
            'checkout': checkout_date.strftime('%Y-%m-%d')
        })

    # Agregar extracciones de fin de semana
    start_date = today
    end_date = today + timedelta(days=days_to_extract - 1)  # Último día del rango
    weekend_extractions = detect_weekend_extractions(start_date, end_date)
    dates.extend(weekend_extractions)

    print(f"📅 Fechas a procesar: {dates[0]['checkin']} hasta {dates[-1]['checkin']} ({len(dates)} días)")
    if weekend_extractions:
        print(f"📅 Extracciones de fin de semana agregadas: {len(weekend_extractions)}")
    print("=" * 80)

    # Estadísticas globales
    total_stats = {
        'hotels_processed': 0,
        'total_sessions_created': 0,
        'total_sessions_updated': 0,
        'total_room_availabilities_created': 0,
        'total_errors': []
    }

    # Procesar cada hotel
    for hotel_idx, hotel in enumerate(hotels, 1):
        hotel_id = hotel['id']
        hotel_name = hotel.get('name', f'Hotel {hotel_id}')
        hotel_slug = hotel.get('url', '')

        if not hotel_slug:
            logger.warning(f"Hotel {hotel_id} no tiene URL, saltando...")
            continue

        print(f"\n🏨 [{hotel_idx}/{len(hotels)}] Procesando hotel: {hotel_name} (ID: {hotel_id})")
        print("-" * 80)

        hotel_stats = {
            'sessions_created': 0,
            'sessions_updated': 0,
            'room_availabilities_created': 0,
            'errors': []
        }

        # Procesar cada fecha para este hotel
        for date_idx, date_info in enumerate(dates, 1):
            checkin = date_info['checkin']
            checkout = date_info['checkout']

            print(f"  📆 [{date_idx}/{len(dates)}] Fecha: {checkin} -> {checkout}")

            # Crear nueva conexión para cada petición
            conn = None
            try:
                conn = get_db_connection()
                # Usar el proxy seleccionado al inicio de la ejecución
                service = HotelScrapingService(conn, proxy=proxy)

                # Construir URL con todos los parámetros requeridos
                from urllib.parse import urlencode, quote_plus
                import hashlib
                import time as time_module
                
                # Generar srpvid (16 caracteres MD5 de microtime)
                microtime = time_module.time()
                srpvid = hashlib.md5(str(microtime).encode()).hexdigest()[:16]
                
                # Parámetros de URL (solo incluir valores no vacíos)
                url_params = {
                    'aid': settings.booking_aid,
                    'label': settings.booking_label,
                    'checkin': checkin,
                    'checkout': checkout,
                    'dest_type': 'hotel',
                    'dist': '0',
                    'group_adults': '1',
                    'group_children': '0',
                    'hapos': '1',
                    'hpos': '1',
                    'no_rooms': '1',
                    'req_adults': '1',
                    'req_children': '0',
                    'room1': 'A,A',  # Se codificará como A%2CA
                    'sb_price_type': 'total',
                    'sr_order': 'popularity',
                    'srepoch': str(int(time_module.time())),
                    'srpvid': srpvid,
                    'type': 'total',
                    'ucfs': '1',
                    'selected_currency': settings.booking_currency,
                }
                
                # Construir URL con código de país e idioma en el slug
                # Formato: https://www.booking.com/hotel/{country_code}/{hotel_slug}.{language_code}.html
                base_url = f"https://www.booking.com/hotel/{settings.booking_country_code}/{hotel_slug}.{settings.booking_language_code}.html"
                query_string = urlencode(url_params, quote_via=quote_plus, safe='')
                
                hotel_url = f"{base_url}?{query_string}"

                # Parámetros de scraping
                scraping_params = {
                    'checkin_date': checkin,
                    'checkout_date': checkout,
                    'adults': 1,
                    'children': 0,
                    'currency': settings.booking_currency,
                    'extraction_mode': 'daily'
                }

                # Realizar scraping
                results = service.scrape_hotel(
                    hotel_id=hotel_id,
                    hotel_url=hotel_url,
                    scraping_params=scraping_params,
                    proxy_id=None
                )

                # Acumular estadísticas
                hotel_stats['sessions_created'] += results.get('sessions_created', 0)
                hotel_stats['sessions_updated'] += results.get('sessions_updated', 0)
                hotel_stats['room_availabilities_created'] += results.get('room_availabilities_created', 0)

                if results.get('errors'):
                    hotel_stats['errors'].extend(results['errors'])

                print(f"    ✅ Sesiones: {results.get('sessions_created', 0)} creadas, {results.get('sessions_updated', 0)} actualizadas | Habitaciones: {results.get('room_availabilities_created', 0)}")

                if results.get('errors'):
                    print(f"    ⚠️  Errores: {len(results['errors'])}")
                    for error in results['errors']:
                        logger.error(f"      - {error}")

            except Exception as e:
                error_msg = f"Error procesando fecha {checkin} para hotel {hotel_id}: {str(e)}"
                logger.error(error_msg)
                hotel_stats['errors'].append(error_msg)
                print(f"    ❌ Error: {str(e)}")

            finally:
                # Cerrar conexión después de cada petición
                if conn:
                    try:
                        conn.close()
                        logger.debug(f"Conexión cerrada para fecha {checkin}")
                    except Exception as e:
                        logger.warning(f"Error cerrando conexión: {e}")

            # Delay aleatorio entre peticiones (15-45 segundos)
            # No hacer delay después de la última petición del último hotel
            if not (hotel_idx == len(hotels) and date_idx == len(dates)):
                delay = random.randint(7, 20)
                print(f"    ⏳ Esperando {delay} segundos antes de la siguiente petición...")
                time.sleep(delay)

        # Resumen del hotel
        print(f"\n  📊 Resumen hotel {hotel_name}:")
        print(f"     - Sesiones creadas: {hotel_stats['sessions_created']}")
        print(f"     - Sesiones actualizadas: {hotel_stats['sessions_updated']}")
        print(f"     - Habitaciones creadas: {hotel_stats['room_availabilities_created']}")
        print(f"     - Errores: {len(hotel_stats['errors'])}")

        # Acumular en estadísticas globales
        total_stats['hotels_processed'] += 1
        total_stats['total_sessions_created'] += hotel_stats['sessions_created']
        total_stats['total_sessions_updated'] += hotel_stats['sessions_updated']
        total_stats['total_room_availabilities_created'] += hotel_stats['room_availabilities_created']
        total_stats['total_errors'].extend(hotel_stats['errors'])

    # Resumen final
    print("\n" + "=" * 80)
    print("📈 RESUMEN FINAL")
    print("=" * 80)
    print(f"Hoteles procesados: {total_stats['hotels_processed']}")
    print(f"Total sesiones creadas: {total_stats['total_sessions_created']}")
    print(f"Total sesiones actualizadas: {total_stats['total_sessions_updated']}")
    print(f"Total habitaciones creadas: {total_stats['total_room_availabilities_created']}")
    print(f"Total errores: {len(total_stats['total_errors'])}")

    if total_stats['total_errors']:
        print("\n⚠️  Errores encontrados:")
        for error in total_stats['total_errors'][:10]:  # Mostrar solo los primeros 10
            print(f"  - {error}")
        if len(total_stats['total_errors']) > 10:
            print(f"  ... y {len(total_stats['total_errors']) - 10} errores más")

    # Limpieza final de procesos zombies y archivos temporales
    logger.info("🧹 Limpieza final: eliminando procesos Chrome/ChromeDriver zombies...")
    kill_chrome_processes()
    cleanup_old_temp_dirs(max_age_hours=1)  # Limpiar archivos de más de 1 hora
    
    print("\n✅ Proceso completado!")