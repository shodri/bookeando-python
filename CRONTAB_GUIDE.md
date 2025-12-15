# Guía de Ejecución y Programación con Crontab

## 🚀 Ejecución del Script

### Ejecución Manual

```bash
# Desde el directorio del proyecto
cd /ruta/al/bookeando-v5

# Activar entorno virtual (si usas venv)
source venv/bin/activate

# O si usas Poetry
poetry shell

# Ejecutar el scraper
python -m src.main --days 15
```

### Ejecución con Script Shell

El proyecto incluye `run_booking_scraper.sh` que maneja la limpieza automática:

```bash
# Dar permisos de ejecución (solo la primera vez)
chmod +x run_booking_scraper.sh

# Ejecutar
./run_booking_scraper.sh 15
```

### Ejecución en Background

```bash
# Ejecutar en background y guardar output
nohup python -m src.main --days 15 > scraper_output.log 2>&1 &

# Ver el proceso
ps aux | grep "src.main"

# Ver logs en tiempo real
tail -f scraper_output.log
```

---

## ⏰ Programación con Crontab

### Configuración Básica

#### 1. Editar Crontab

```bash
# Abrir editor de crontab
crontab -e
```

#### 2. Agregar Tarea

Agrega una línea al final del archivo con el formato:

```
MINUTO HORA DIA MES DIA_SEMANA COMANDO
```

### Ejemplos de Configuración

#### Ejemplo 1: Ejecutar Todos los Días a las 2:00 AM

```bash
# Editar crontab
crontab -e

# Agregar esta línea:
0 2 * * * cd /var/www/scripts/scrapers/bookeando-v5 && /usr/bin/python3 -m src.main --days 15 >> /var/log/scraper_cron.log 2>&1
```

**Explicación:**
- `0 2 * * *` = Todos los días a las 2:00 AM
- `cd /ruta/al/proyecto` = Cambiar al directorio del proyecto
- `>> /var/log/scraper_cron.log 2>&1` = Redirigir output y errores a un log

#### Ejemplo 2: Ejecutar Cada 6 Horas

```bash
0 */6 * * * cd /var/www/scripts/scrapers/bookeando-v5 && /usr/bin/python3 -m src.main --days 7 >> /var/log/scraper_cron.log 2>&1
```

**Explicación:**
- `0 */6 * * *` = Cada 6 horas (00:00, 06:00, 12:00, 18:00)

#### Ejemplo 3: Ejecutar Solo en Días Laborables (Lunes-Viernes) a las 3:00 AM

```bash
0 3 * * 1-5 cd /var/www/scripts/scrapers/bookeando-v5 && /usr/bin/python3 -m src.main --days 15 >> /var/log/scraper_cron.log 2>&1
```

**Explicación:**
- `0 3 * * 1-5` = Lunes a Viernes a las 3:00 AM

#### Ejemplo 4: Usar el Script Shell con Crontab

```bash
# Usar el script run_booking_scraper.sh
0 2 * * * /var/www/scripts/scrapers/bookeando-v5/run_booking_scraper.sh 15 >> /var/log/scraper_cron.log 2>&1
```

#### Ejemplo 5: Con Entorno Virtual

```bash
# Si usas venv
0 2 * * * cd /var/www/scripts/scrapers/bookeando-v5 && /var/www/scripts/scrapers/bookeando-v5/venv/bin/python -m src.main --days 15 >> /var/log/scraper_cron.log 2>&1

# Si usas Poetry
0 2 * * * cd /var/www/scripts/scrapers/bookeando-v5 && /usr/local/bin/poetry run python -m src.main --days 15 >> /var/log/scraper_cron.log 2>&1
```

### Configuración Completa Recomendada

```bash
# Editar crontab
crontab -e

# Agregar estas líneas:

# Variables de entorno (opcional pero recomendado)
PATH=/usr/local/bin:/usr/bin:/bin
SHELL=/bin/bash

# Ejecutar scraper todos los días a las 2:00 AM
0 2 * * * cd /var/www/scripts/scrapers/bookeando-v5 && /usr/bin/python3 -m src.main --days 15 >> /var/log/scraper_cron.log 2>&1

# Limpiar logs antiguos cada domingo a las 1:00 AM (mantener solo últimos 30 días)
0 1 * * 0 find /var/log -name "scraper*.log" -mtime +30 -delete
```

---

## 🔍 Verificar y Gestionar Crontab

### Ver Tareas Programadas

```bash
# Ver todas las tareas del usuario actual
crontab -l

# Ver tareas de otro usuario (requiere permisos)
sudo crontab -u usuario -l
```

### Eliminar Tareas

```bash
# Eliminar todas las tareas
crontab -r

# Editar y eliminar manualmente
crontab -e
# (elimina la línea que no quieres)
```

### Ver Logs de Crontab

```bash
# Ver logs del sistema (Ubuntu/Debian)
sudo tail -f /var/log/syslog | grep CRON

# Ver logs del sistema (CentOS/RHEL)
sudo tail -f /var/log/cron

# Ver tu log personalizado
tail -f /var/log/scraper_cron.log
```

### Probar Ejecución Manual

Antes de agregar a crontab, prueba que el comando funciona:

```bash
# Probar el comando completo
cd /var/www/scripts/scrapers/bookeando-v5 && /usr/bin/python3 -m src.main --days 1

# Si funciona, entonces agrégalo a crontab
```

---

## 📋 Formato de Crontab - Referencia Rápida

```
* * * * * comando
│ │ │ │ │
│ │ │ │ └─── Día de la semana (0-7, donde 0 y 7 = domingo)
│ │ │ └───── Mes (1-12)
│ │ └─────── Día del mes (1-31)
│ └───────── Hora (0-23)
└─────────── Minuto (0-59)
```

### Ejemplos de Patrones

| Patrón | Descripción |
|--------|-------------|
| `* * * * *` | Cada minuto |
| `0 * * * *` | Cada hora (al inicio) |
| `0 */2 * * *` | Cada 2 horas |
| `0 9 * * *` | Todos los días a las 9:00 AM |
| `0 9 * * 1-5` | Lunes a Viernes a las 9:00 AM |
| `0 9 1 * *` | Primer día de cada mes a las 9:00 AM |
| `0 9 * * 0` | Todos los domingos a las 9:00 AM |
| `*/15 * * * *` | Cada 15 minutos |
| `0 0,12 * * *` | A las 12:00 AM y 12:00 PM |

---

## ⚙️ Configuración Avanzada

### Variables de Entorno en Crontab

Si necesitas variables de entorno específicas:

```bash
# En crontab, antes de los comandos:
PATH=/usr/local/bin:/usr/bin:/bin
HOME=/home/usuario
DB_HOST=64.227.108.76
# etc...

# Luego tus comandos
0 2 * * * cd /ruta/al/proyecto && python -m src.main --days 15
```

**Nota:** Es mejor usar el archivo `.env` del proyecto en lugar de variables en crontab.

### Usar Script Wrapper

Crea un script wrapper para mayor control:

```bash
#!/bin/bash
# /var/www/scripts/scrapers/bookeando-v5/run_scraper_cron.sh

# Cambiar al directorio del proyecto
cd /var/www/scripts/scrapers/bookeando-v5

# Activar entorno virtual (si aplica)
source venv/bin/activate

# Ejecutar scraper
python -m src.main --days 15

# Código de salida
exit_code=$?

# Enviar email si hay error (opcional, requiere mail configurado)
if [ $exit_code -ne 0 ]; then
    echo "Error en scraper. Código: $exit_code" | mail -s "Error Scraper" admin@example.com
fi

exit $exit_code
```

Luego en crontab:

```bash
0 2 * * * /var/www/scripts/scrapers/bookeando-v5/run_scraper_cron.sh >> /var/log/scraper_cron.log 2>&1
```

### Múltiples Ejecuciones con Diferentes Parámetros

```bash
# Ejecutar con 15 días a las 2:00 AM
0 2 * * * cd /ruta/al/proyecto && python -m src.main --days 15 >> /var/log/scraper_15d.log 2>&1

# Ejecutar con 30 días a las 3:00 AM
0 3 * * * cd /ruta/al/proyecto && python -m src.main --days 30 >> /var/log/scraper_30d.log 2>&1
```

---

## 🐛 Solución de Problemas

### El Script No Se Ejecuta

1. **Verificar permisos:**
   ```bash
   ls -l /ruta/al/proyecto/run_booking_scraper.sh
   chmod +x /ruta/al/proyecto/run_booking_scraper.sh
   ```

2. **Verificar ruta de Python:**
   ```bash
   which python3
   # Usa la ruta completa en crontab: /usr/bin/python3
   ```

3. **Verificar variables de entorno:**
   ```bash
   # Crontab no carga .bashrc, asegúrate de usar rutas absolutas
   ```

4. **Verificar logs:**
   ```bash
   tail -f /var/log/scraper_cron.log
   tail -f /var/log/syslog | grep CRON
   ```

### El Script Se Ejecuta Pero Falla

1. **Verificar que el archivo `.env` existe:**
   ```bash
   ls -la /ruta/al/proyecto/.env
   ```

2. **Verificar permisos de escritura en logs:**
   ```bash
   mkdir -p /var/log
   touch /var/log/scraper_cron.log
   chmod 666 /var/log/scraper_cron.log
   ```

3. **Ejecutar manualmente para ver errores:**
   ```bash
   cd /ruta/al/proyecto
   /usr/bin/python3 -m src.main --days 1
   ```

### El Script Tarda Mucho

1. **Ajustar timeout en crontab (opcional):**
   ```bash
   # Agregar timeout de 2 horas
   0 2 * * * timeout 7200 cd /ruta/al/proyecto && python -m src.main --days 15
   ```

2. **Reducir número de días:**
   ```bash
   python -m src.main --days 7  # En lugar de 15
   ```

---

## 📊 Monitoreo

### Verificar Última Ejecución

```bash
# Ver cuándo se ejecutó por última vez
grep "Proceso completado" /var/log/scraper_cron.log | tail -1

# Ver si hay errores recientes
grep -i error /var/log/scraper_cron.log | tail -10
```

### Crear Script de Monitoreo

```bash
#!/bin/bash
# check_scraper_status.sh

LOG_FILE="/var/log/scraper_cron.log"
LAST_RUN=$(grep "Proceso completado" $LOG_FILE | tail -1 | awk '{print $1, $2}')

if [ -z "$LAST_RUN" ]; then
    echo "⚠️  No se encontró ejecución reciente"
    exit 1
else
    echo "✅ Última ejecución: $LAST_RUN"
    exit 0
fi
```

Agregar a crontab para verificar cada hora:

```bash
0 * * * * /ruta/al/check_scraper_status.sh
```

---

## ✅ Checklist de Configuración

Antes de programar con crontab, verifica:

- [ ] El script funciona cuando lo ejecutas manualmente
- [ ] Tienes la ruta completa de Python (`which python3`)
- [ ] El archivo `.env` está configurado correctamente
- [ ] Tienes permisos de escritura en el directorio de logs
- [ ] El directorio del proyecto tiene permisos correctos
- [ ] Has probado el comando completo que vas a usar en crontab
- [ ] Has configurado redirección de logs (`>> logfile 2>&1`)

---

## 📝 Ejemplo Completo de Configuración

```bash
# 1. Crear directorio de logs
sudo mkdir -p /var/log
sudo touch /var/log/scraper_cron.log
sudo chmod 666 /var/log/scraper_cron.log

# 2. Verificar ruta de Python
which python3
# Resultado ejemplo: /usr/bin/python3

# 3. Probar comando manualmente
cd /var/www/scripts/scrapers/bookeando-v5
/usr/bin/python3 -m src.main --days 1

# 4. Si funciona, editar crontab
crontab -e

# 5. Agregar esta línea:
0 2 * * * cd /var/www/scripts/scrapers/bookeando-v5 && /usr/bin/python3 -m src.main --days 15 >> /var/log/scraper_cron.log 2>&1

# 6. Guardar y salir (en vim: ESC, luego :wq, ENTER)

# 7. Verificar que se agregó
crontab -l

# 8. Esperar a la hora programada o probar manualmente
```

---

**Última actualización:** Diciembre 2024

