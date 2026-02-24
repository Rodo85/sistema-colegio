# Nota: Cómo probar la Fase 4 manualmente

## 1. Acceso al resumen

- Desde la lista de actividades: "Ver resumen" en el banner.
- URL: `/docente/asignacion/<id>/resumen-evaluacion/`

## 2. Filtros

- Período: selector de períodos del curso lectivo.

## 3. Columnas mostradas

Por estudiante:
- **TAREAS**: Obtenidos, Máximos, % logro, % comp., Aporte
- **COTIDIANOS**: Obtenidos, Máximos, % logro, % comp., Aporte

## 4. Detalle por estudiante

- Clic en el nombre del estudiante → desglose por actividad.
- Muestra: actividades incluidas, puntos máximos por actividad, puntos obtenidos por actividad, total acumulado.

## 5. Casos de prueba obligatorios

### Caso 1: Cotidiano 50% logro, 60% componente → aporte 30
- Componente Cotidiano: 100 puntos máximos acumulados.
- Estudiante: 50 puntos obtenidos.
- % logro = 50%.
- Si Cotidiano vale 60% en el esquema → aporte = 30.

### Caso 2: Tareas 75% logro, 10% componente → aporte 7.5
- Componente Tareas: 40 máximos, 30 obtenidos.
- % logro = 75%.
- Si Tareas vale 10% → aporte = 7.5.

### Caso 3: Sin indicadores / máximos = 0
- Actividad sin indicadores activos o sin actividades en el período.
- % logro = 0 (sin error).

## 6. Configuración de porcentajes

Los porcentajes (TAREAS 10%, COTIDIANO 60%, etc.) vienen del **Esquema de evaluación** asignado a la materia (SubareaCursoLectivo → eval_scheme). La asignación docente guarda un snapshot (eval_scheme_snapshot).

Si el esquema no tiene TAREAS o COTIDIANO configurados, el aporte será 0.

## 7. Archivos modificados/creados (Fase 4)

- `libro_docente/services.py` – `obtener_porcentaje_componente_esquema`, `calcular_resumen_componente_estudiante`, `calcular_resumen_evaluacion_completo`
- `libro_docente/views.py` – `resumen_evaluacion_view`, `resumen_estudiante_detalle_view`
- `libro_docente/urls.py` – ruta `resumen_estudiante_detalle`
- `libro_docente/templates/libro_docente/resumen_evaluacion.html`
- `libro_docente/templates/libro_docente/resumen_estudiante_detalle.html`
- `libro_docente/REGLAS_ACUMULADO_FASE4.md` – regla documentada de actividades que cuentan
- `libro_docente/NOTA_PRUEBA_FASE4.md` – esta nota
