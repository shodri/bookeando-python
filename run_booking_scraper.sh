#!/bin/bash

# Función de limpieza de procesos Chrome/ChromeDriver
cleanup_chrome_processes() {
    echo "🧹 Limpiando procesos Chrome/ChromeDriver zombies..."
    pkill -9 -f "chrome.*--headless" 2>/dev/null || true
    pkill -9 -f "chromedriver" 2>/dev/null || true
    sleep 1
}

# Función de limpieza de archivos temporales antiguos
cleanup_temp_files() {
    echo "🧹 Limpiando archivos temporales antiguos..."
    # Buscar y eliminar directorios temporales de Chrome con más de 1 hora
    # Buscar directorios que contengan "Default" (directorios de user-data-dir de Chrome)
    find /tmp -type d -name "tmp*" -mmin +60 2>/dev/null | while read dir; do
        if [ -d "$dir/Default" ] || [ -f "$dir/.org.chromium.Chromium.*" ] 2>/dev/null; then
            rm -rf "$dir" 2>/dev/null || true
        fi
    done
    # Limpiar directorios tmp vacíos
    find /tmp -type d -name "tmp*" -empty -delete 2>/dev/null || true
}

# Log con timestamp
LOG_FILE="/var/www/scripts/scrapers/logs/scraper_$(date +\%Y\%m\%d).log"

# Función de limpieza final (se ejecuta siempre)
cleanup_final() {
    cleanup_chrome_processes
    cleanup_temp_files
    echo "✅ Limpieza final completada" >> "$LOG_FILE" 2>&1
}

# Configurar trap para asegurar limpieza en caso de interrupción
trap cleanup_final EXIT INT TERM

{
    echo "=== Ejecución iniciada: $(date) ==="
    
    # Limpieza inicial
    cleanup_chrome_processes
    cleanup_temp_files

    # Activar entorno virtual y ejecutar
    cd /var/www/scripts/scrapers
    source venv/bin/activate
    python booking_scraper.py "$1"
    EXIT_CODE=$?

    # Limpieza después de la ejecución
    cleanup_chrome_processes
    cleanup_temp_files

    echo "=== Ejecución finalizada: $(date) ==="
    echo ""
    
    exit $EXIT_CODE
} >> "$LOG_FILE" 2>&1