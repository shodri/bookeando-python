# Cómo Ejecutar el Scraper en Segundo Plano

## 🚀 Ejecución Rápida (en Background)

### Opción 1: Con nohup (Recomendada)

```bash
# Ejecutar en segundo plano con 5 días
nohup ./run_booking_scraper.sh 5 &

# Ejecutar en segundo plano con 15 días
nohup ./run_booking_scraper.sh 15 &
```

**¿Qué hace `nohup ... &`?**
- `nohup` = El proceso sigue corriendo aunque cierres la terminal
- `&` = Ejecuta en segundo plano y te devuelve la línea de comando

---

### Opción 2: Solo con & (Más simple)

```bash
# Ejecutar en segundo plano
./run_booking_scraper.sh 5 &

# Desvincularlo de la terminal (opcional, para poder cerrar la terminal)
disown
```

---

## 📋 Ver el Progreso

Los logs se guardan automáticamente en `logs/scraper_YYYYMMDD.log`

```bash
# Ver logs en tiempo real
tail -f logs/scraper_$(date +%Y%m%d).log

# Ver últimas 50 líneas del log
tail -50 logs/scraper_$(date +%Y%m%d).log

# Ver todos los logs disponibles
ls -la logs/
```

---

## 🔍 Ver si el Proceso Está Corriendo

```bash
# Ver procesos del scraper
ps aux | grep "src.main"

# Ver procesos de Python activos
ps aux | grep python
```

---

## ⛔ Detener el Proceso

```bash
# Encontrar el PID (Process ID)
ps aux | grep "src.main"

# Matar el proceso (reemplazar PID con el número)
kill PID

# O matar forzadamente si no responde
kill -9 PID
```

---

## 📝 Ejemplos Completos

### Ejecutar y ver progreso inmediatamente

```bash
# 1. Ejecutar en background
nohup ./run_booking_scraper.sh 5 &

# 2. Ver el progreso (Ctrl+C para salir del tail sin matar el scraper)
tail -f logs/scraper_$(date +%Y%m%d).log
```

### Ejecutar con días personalizados

```bash
# 7 días
nohup ./run_booking_scraper.sh 7 &

# 15 días
nohup ./run_booking_scraper.sh 15 &

# 30 días
nohup ./run_booking_scraper.sh 30 &
```

---

## ⚠️ Notas Importantes

1. **Primera vez:** Asegurate de dar permisos de ejecución:
   ```bash
   chmod +x run_booking_scraper.sh
   ```

2. **Directorio:** Ejecutá siempre desde el directorio del proyecto:
   ```bash
   cd /ruta/al/bookeando-v5
   ```

3. **El parámetro es la cantidad de días** a scrapear (por defecto usa 5 si no lo pasás)

4. **Los logs tienen fecha:** Cada día crea un archivo nuevo en `logs/`

---

## 🔄 Resumen Rápido

| Acción | Comando |
|--------|---------|
| Ejecutar en background | `nohup ./run_booking_scraper.sh 5 &` |
| Ver logs en tiempo real | `tail -f logs/scraper_$(date +%Y%m%d).log` |
| Ver si está corriendo | `ps aux \| grep "src.main"` |
| Detener proceso | `kill PID` |

---

**Última actualización:** Diciembre 2024
