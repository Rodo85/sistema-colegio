# Reglas del resumen acumulado (Fase 4)

## Actividades que cuentan en el acumulado

**Regla MVP aplicada:**
- **Estados**: Solo actividades en estado ACTIVA o CERRADA (no BORRADOR).
- **Indicadores**: La actividad debe tener al menos un indicador activo.
- **Parciales**: Se permiten actividades sin puntajes registrados; aportan 0 a obtenidos pero sí a máximos.

### Justificación
- BORRADOR: no está lista para evaluación.
- ACTIVA/CERRADA: el docente ya la considera evaluable.
- Sin indicadores: no aporta nada al cálculo.
- Parciales: un estudiante puede no tener puntaje en una actividad (aún no calificada); el máximo de esa actividad cuenta para el total máximo del componente.

## Cálculos

### Por componente (TAREAS o COTIDIANOS)
- `puntos_obtenidos_componente` = SUM(puntaje_obtenido) de todas las actividades del tipo en el período
- `puntos_maximos_componente` = SUM(escala_max de indicadores activos de esas actividades)
- `porcentaje_logro_componente` = (obtenidos / máximos) * 100 si máximos > 0, si no 0

### Aporte a nota final
- `aporte` = (porcentaje_logro_componente / 100) * porcentaje_componente
- `porcentaje_componente` se obtiene del esquema de evaluación de la asignación (EsquemaEvalComponente).
- Si el componente no está en el esquema, aporte = 0.

## Mapeo tipo → esquema
- ActividadEvaluacion.TAREA → ComponenteEval codigo "TAREAS" o "TAREA"
- ActividadEvaluacion.COTIDIANO → ComponenteEval codigo "COTIDIANO"
