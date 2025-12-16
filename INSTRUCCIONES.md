# Instrucciones de Uso y Testing - Booking Scraper v5

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Instalación](#instalación)
3. [Configuración](#configuración)
4. [Uso del Software](#uso-del-software)
5. [Testing](#testing)
6. [Solución de Problemas](#solución-de-problemas)

---

## 🔧 Requisitos Previos

### Software Necesario

- **Python 3.10 o superior**
- **Poetry** (recomendado) o **pip**
- **Chrome/Chromium** instalado en el sistema
- **ChromeDriver** (se instala automáticamente con webdriver-manager)
- **MySQL** con acceso a la base de datos `bookeandov5`

### Verificar Instalaciones

```bash
# Verificar Python
python --version  # Debe ser 3.10+

# Verificar Poetry (opcional)
poetry --version

# Verificar Chrome
chrome --version  # o chromium --version en Linux
```

---

## 📦 Instalación

### Opción 1: Usando Poetry (Recomendado)

```bash
# 1. Instalar Poetry si no lo tienes
# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Linux/Mac
curl -sSL https://install.python-poetry.org | python3 -

# 2. Instalar dependencias del proyecto
poetry install

# 3. Activar el entorno virtual
poetry shell
```

### Opción 2: Usando pip

```bash
# 1. Crear entorno virtual
python -m venv venv

# 2. Activar entorno virtual
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. Instalar dependencias desde pyproject.toml
pip install -e .
```

---

## ⚙️ Configuración

### 1. Crear Archivo de Variables de Entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# O crear manualmente el archivo .env
```

### 2. Editar Archivo `.env`

Abre el archivo `.env` y configura las siguientes variables:

```env
# ============================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================
DB_HOST=64.227.108.76
DB_USER=tenancy
DB_PASSWORD=tu_contraseña_aqui
DB_NAME=bookeandov5
DB_PORT=3306

# ============================================
# CONFIGURACIÓN DE LOGGING
# ============================================
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json                   # json o text
LOG_FILE=logs/scraper.log         # Ruta del archivo de log

# ============================================
# CONFIGURACIÓN DE SCRAPING
# ============================================
SCRAPING_DELAY_MIN=7              # Delay mínimo entre peticiones (segundos)
SCRAPING_DELAY_MAX=20             # Delay máximo entre peticiones (segundos)
SCRAPING_TIMEOUT=30               # Timeout de scraping (segundos)
HEADLESS_MODE=true                # true para servidor, false para ver el navegador

# ============================================
# CONFIGURACIÓN DE CHROME
# ============================================
CHROME_DEBUG_PORT=0               # 0 para puerto automático
CHROME_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36


```

### 3. Verificar Configuración

```bash
# Probar que las variables se cargan correctamente
python -c "from src.config.settings import settings; print(settings.db_host)"
```

---

## 🚀 Uso del Software

### Uso Básico

```bash
# Ejecutar el scraper con configuración por defecto (15 días)
python -m src.main

# Ejecutar con número específico de días
python -m src.main --days 30

# Ver ayuda
python -m src.main --help
```

### Uso Programático

#### Ejemplo 1: Scraping Simple de un Hotel

```python
from src.infrastructure.database.connection import get_db_connection
from src.infrastructure.database.repositories import HotelRepository, RoomRepository
from src.application.update_prices import UpdatePricesService

# Obtener conexión a la base de datos
conn = get_db_connection()

# Crear servicio de actualización de precios
service = UpdatePricesService(conn, proxy=None)

# Actualizar precios de un hotel específico
results = service.update_hotel_prices(
    hotel_id=1,
    hotel_url="https://www.booking.com/hotel/es/hotel-slug.html",
    checkin_date="2024-01-15",
    checkout_date="2024-01-16",
    adults=1,
    children=0,
    currency="EUR"
)

print(f"Sesiones creadas: {results['sessions_created']}")
print(f"Habitaciones creadas: {results['room_availabilities_created']}")

conn.close()
```

#### Ejemplo 2: Scraping con Rango de Fechas

```python
from datetime import datetime, timedelta
from src.application.update_prices import UpdatePricesService
from src.infrastructure.database.connection import get_db_connection

conn = get_db_connection()
service = UpdatePricesService(conn, proxy=None)

# Definir rango de fechas
start_date = datetime(2024, 1, 15)
end_date = datetime(2024, 1, 30)

# Actualizar precios para todo el rango
results = service.update_hotel_for_date_range(
    hotel_id=1,
    hotel_url="https://www.booking.com/hotel/es/hotel-slug.html",
    start_date=start_date,
    end_date=end_date,
    adults=1,
    children=0,
    currency="EUR"
)

print(f"Total sesiones: {results['sessions_created']}")
print(f"Total habitaciones: {results['room_availabilities_created']}")

conn.close()
```

#### Ejemplo 3: Usar Solo el Scraper (Sin Base de Datos)

```python
from src.infrastructure.scraping.booking_scraper import BookingScraper

# Crear scraper
scraper = BookingScraper(proxy=None)

try:
    # Scrapear hotel
    data = scraper.scrape_hotel(
        hotel_url="https://www.booking.com/hotel/es/hotel-slug.html",
        checkin_date="2024-01-15",
        checkout_date="2024-01-16"
    )
    
    # Procesar datos
    print(f"Hotel: {data.hotel_url}")
    print(f"Éxito: {data.success}")
    print(f"Habitaciones encontradas: {len(data.room_availabilities)}")
    
    for room in data.room_availabilities:
        print(f"  - {room.room_type_name}: €{room.final_price}")
        
finally:
    scraper.close()
```

### Uso con Script Shell (Linux/Mac)

El script `run_booking_scraper.sh` está disponible para ejecución automatizada:

```bash
# Dar permisos de ejecución
chmod +x run_booking_scraper.sh

# Ejecutar
./run_booking_scraper.sh 15  # 15 días
```

---

## 🧪 Testing

### Instalación de Dependencias de Testing

Las dependencias de testing ya están incluidas en `pyproject.toml`. Si usas pip:

```bash
pip install pytest pytest-mock pytest-cov
```

### Ejecutar Todos los Tests

```bash
# Ejecutar todos los tests
pytest

# Con output detallado
pytest -v

# Con coverage
pytest --cov=src --cov-report=html --cov-report=term-missing
```

### Ejecutar Tests Específicos

```bash
# Solo tests unitarios
pytest tests/unit/

# Solo tests de integración
pytest tests/integration/

# Test específico
pytest tests/unit/test_price_cleaning.py

# Test específico con nombre
pytest tests/unit/test_price_cleaning.py::TestPriceService::test_clean_price_with_euro_symbol
```

### Ejecutar Tests con Marcadores

```bash
# Solo tests unitarios (marcador)
pytest -m unit

# Solo tests de integración (marcador)
pytest -m integration
```

### Ver Coverage Report

```bash
# Generar reporte HTML
pytest --cov=src --cov-report=html

# Abrir reporte (el archivo estará en htmlcov/index.html)
# Windows
start htmlcov/index.html

# Linux
xdg-open htmlcov/index.html

# Mac
open htmlcov/index.html
```

### Ejecutar Tests en Modo Watch (Desarrollo)

```bash
# Instalar pytest-watch
pip install pytest-watch

# Ejecutar en modo watch
ptw tests/
```

### Estructura de Tests

```
tests/
├── unit/                          # Tests unitarios (sin dependencias externas)
│   ├── test_price_cleaning.py    # Tests de limpieza de precios
│   ├── test_text_extraction.py   # Tests de extracción de texto
│   └── test_weekend_detection.py # Tests de detección de fines de semana
└── integration/                   # Tests de integración (con mocks)
    ├── test_scraping_flow.py     # Tests del flujo de scraping
    └── test_repositories.py      # Tests de repositorios
```

### Escribir Nuevos Tests

#### Ejemplo: Test Unitario

```python
# tests/unit/test_my_service.py
import pytest
from src.domain.services import PriceService

def test_my_new_feature():
    """Test description."""
    result = PriceService.clean_price("€100")
    assert result == 100.0
```

#### Ejemplo: Test de Integración con Mock

```python
# tests/integration/test_my_integration.py
from unittest.mock import Mock, patch
import pytest

@patch('src.infrastructure.scraping.booking_scraper.DriverFactory.create_driver')
def test_scraping_with_mock(mock_create_driver):
    """Test scraping with mocked driver."""
    mock_driver = Mock()
    mock_create_driver.return_value = (mock_driver, "/tmp/test", 9222)
    
    # Tu test aquí
    pass
```

### Verificar Type Hints

```bash
# Verificar tipos con mypy
mypy src/

# Verificar tipos específicos
mypy src/domain/
```

---

## 🔍 Solución de Problemas

### Error: "No module named 'src'"

**Solución:**
```bash
# Asegúrate de estar en el directorio raíz del proyecto
cd /ruta/al/bookeando-v5

# Instala el proyecto en modo desarrollo
pip install -e .
```

### Error: "ChromeDriver not found"

**Solución:**
- El ChromeDriver se instala automáticamente con `webdriver-manager`
- Si falla, descarga manualmente desde: https://chromedriver.chromium.org/
- Asegúrate de que Chrome esté instalado

### Error: "Database connection failed"

**Solución:**
1. Verifica que el archivo `.env` existe y tiene las credenciales correctas
2. Verifica que MySQL está corriendo
3. Verifica que puedes conectarte manualmente:
   ```bash
   mysql -h 64.227.108.76 -u tenancy -p bookeandov5
   ```

### Error: "ModuleNotFoundError: No module named 'pydantic_settings'"

**Solución:**
```bash
# Instalar dependencias
poetry install
# o
pip install pydantic-settings
```

### Tests Fallan

**Solución:**
1. Verifica que todas las dependencias están instaladas:
   ```bash
   pip install -e ".[dev]"
   ```

2. Verifica que estás en el directorio correcto:
   ```bash
   pwd  # Debe mostrar el directorio del proyecto
   ```

3. Ejecuta tests con más verbosidad:
   ```bash
   pytest -vv tests/
   ```

### Chrome no se cierra correctamente

**Solución:**
- El código incluye limpieza automática de procesos
- Si persiste, ejecuta manualmente:
  ```bash
  # Linux/Mac
  pkill -9 chrome
  pkill -9 chromedriver
  
  # Windows (PowerShell)
  Get-Process chrome | Stop-Process -Force
  Get-Process chromedriver | Stop-Process -Force
  ```

### Logs no se generan

**Solución:**
1. Verifica que el directorio `logs/` existe:
   ```bash
   mkdir -p logs
   ```

2. Verifica permisos de escritura en el directorio

3. Verifica la configuración en `.env`:
   ```env
   LOG_FILE=logs/scraper.log
   ```

### Proxy no funciona

**Solución:**
1. Verifica que el proxy está en la base de datos:
   ```sql
   SELECT * FROM proxies LIMIT 1;
   ```

2. Verifica el formato del proxy (debe ser `http://ip:port`)

3. Prueba sin proxy primero para aislar el problema

---

## 📊 Monitoreo y Logs

### Ver Logs en Tiempo Real

```bash
# Linux/Mac
tail -f logs/scraper.log

# Windows (PowerShell)
Get-Content logs/scraper.log -Wait
```

### Filtrar Logs por Nivel

```bash
# Solo errores
grep ERROR logs/scraper.log

# Solo warnings
grep WARNING logs/scraper.log
```

### Logs en Formato JSON

Si `LOG_FORMAT=json` en `.env`, los logs estarán en formato JSON:

```bash
# Parsear logs JSON (requiere jq)
cat logs/scraper.log | jq '.'
```

---

## 🔐 Seguridad

### ⚠️ IMPORTANTE: Nunca commitees el archivo `.env`

El archivo `.env` contiene credenciales sensibles y está en `.gitignore`. 

**Siempre:**
- ✅ Usa `.env.example` como plantilla
- ✅ Mantén `.env` local
- ✅ Rota las contraseñas regularmente
- ✅ Usa diferentes credenciales para desarrollo y producción

---

## 📚 Recursos Adicionales

### Documentación de Dependencias

- [Selenium](https://www.selenium.dev/documentation/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/usage/settings/)
- [Poetry](https://python-poetry.org/docs/)
- [Pytest](https://docs.pytest.org/)

### Estructura del Proyecto

Ver `README.md` para más detalles sobre la arquitectura del proyecto.

---

## 💡 Tips y Mejores Prácticas

1. **Siempre usa un entorno virtual** para aislar dependencias
2. **Ejecuta tests antes de commitear** cambios importantes
3. **Revisa los logs** regularmente para detectar problemas
4. **Usa proxies rotativos** para evitar bloqueos
5. **Configura delays apropiados** para no sobrecargar el servidor
6. **Mantén Chrome actualizado** para evitar problemas de compatibilidad

---

## 🆘 Soporte

Si encuentras problemas:

1. Revisa esta documentación
2. Revisa los logs en `logs/scraper.log`
3. Ejecuta los tests para verificar que todo funciona
4. Verifica la configuración en `.env`

---

**Última actualización:** Diciembre 2024

