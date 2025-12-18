# Extracción de Precios: Viernes y Fines de Semana

## ¿Qué sucede cuando la extracción toca un viernes?

### Caso 1: Extraer 3 días y el último día es viernes

**Ejemplo:** Si hoy es **miércoles** y solicitas extraer **3 días**:

#### Extracciones diarias generadas:
- **Día 1:** Miércoles → Jueves
- **Día 2:** Jueves → Viernes  
- **Día 3:** Viernes → Sábado

#### Extracciones de fin de semana adicionales:
- **Viernes → Domingo** (2 días)

**Resultado:** Se extraen **4 fechas en total**:
1. Miércoles → Jueves
2. Jueves → Viernes
3. Viernes → Sábado
4. Viernes → Domingo ⭐ (extracción adicional de fin de semana)

**Conclusión:** ✅ **SÍ se extrae el fin de semana**, pero como una extracción adicional de 2 días (viernes → domingo), no solo como parte de las extracciones diarias.

---

### Caso 2: Extraer 3 días y el último día es sábado

**Ejemplo:** Si hoy es **jueves** y solicitas extraer **3 días**:

#### Extracciones diarias generadas:
- **Día 1:** Jueves → Viernes
- **Día 2:** Viernes → Sábado
- **Día 3:** Sábado → Domingo

#### Extracciones de fin de semana adicionales:
- **Viernes → Domingo** (2 días)
- **Sábado → Lunes** (2 días)

**Resultado:** Se extraen **5 fechas en total**:
1. Jueves → Viernes
2. Viernes → Sábado
3. Sábado → Domingo
4. Viernes → Domingo ⭐ (extracción adicional de fin de semana)
5. Sábado → Lunes ⭐ (extracción adicional de fin de semana)

**Conclusión:** ✅ **SÍ se extraen los fines de semana**, tanto viernes → domingo como sábado → lunes, como extracciones adicionales.

---

## ¿Cómo funciona la detección de fines de semana?

El sistema detecta automáticamente los fines de semana en el rango de fechas solicitado y agrega extracciones adicionales:

1. **Viernes detectado:** Crea extracción **Viernes → Domingo** (2 días)
2. **Sábado detectado:** Crea extracción **Sábado → Lunes** (2 días)

Estas extracciones se **agregan** a las extracciones diarias normales, no las reemplazan.

---

## Resumen

- ✅ Si el último día de extracción es **viernes**: Se extrae el fin de semana (viernes → domingo)
- ✅ Si el último día de extracción es **sábado**: Se extraen ambos fines de semana (viernes → domingo y sábado → lunes)
- ✅ Las extracciones de fin de semana son **adicionales** a las extracciones diarias
- ✅ Las extracciones de fin de semana siempre son de **2 días** (check-in viernes/sábado, check-out domingo/lunes)
