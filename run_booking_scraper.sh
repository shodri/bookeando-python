#!/bin/bash

# Obtener el directorio del script (ruta relativa o absoluta)
# Si se pasa como parámetro, usar ese; si no, usar la ubicación del script
if [ -n "$1" ] && [ -d "$1" ]; then
    SCRIPT_DIR="$1"
    shift  # Remover el primer parámetro para que --days quede como $1
else
    # Obtener el directorio donde está el script
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

# Cambiar al directorio del script
cd "$SCRIPT_DIR" || exit 1

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

# Log con timestamp (ruta relativa al directorio del script)
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/scraper_$(date +\%Y\%m\%d).log"

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

    # Crear entorno virtual si no existe
    VENV_DIR="$SCRIPT_DIR/env"
    if [ ! -d "$VENV_DIR" ]; then
        echo "📦 Creando entorno virtual..."
        python3 -m venv "$VENV_DIR"
        if [ $? -ne 0 ]; then
            echo "❌ Error al crear el entorno virtual"
            exit 1
        fi
    fi

    # Activar entorno virtual
    source "$VENV_DIR/bin/activate"
    if [ $? -ne 0 ]; then
        echo "❌ Error al activar el entorno virtual"
        exit 1
    fi

    # Instalar dependencias si es necesario
    if [ ! -f "$VENV_DIR/.requirements_installed" ]; then
        echo "📥 Instalando dependencias..."
        pip install -q --upgrade pip
        pip install -q -r requirements.txt
        touch "$VENV_DIR/.requirements_installed"
    fi

    # Ejecutar el scraper
    python -m src.main --days 5
    EXIT_CODE=$?

    # Limpieza después de la ejecución
    cleanup_chrome_processes
    cleanup_temp_files

    echo "=== Ejecución finalizada: $(date) ==="
    echo ""
    
    exit $EXIT_CODE
} >> "$LOG_FILE" 2>&1