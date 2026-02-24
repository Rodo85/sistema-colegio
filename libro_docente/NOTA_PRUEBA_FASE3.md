# Nota: Cómo probar la Fase 3 manualmente

## 1. Acceso a la pantalla de calificación

- Desde la lista de actividades: clic en "Calificar" en una fila.
- URL directa: `/docente/actividad/<id>/calificar/`

## 2. Estructura de la grilla

- **Filas**: estudiantes del grupo/subgrupo de la actividad.
- **Columnas dinámicas**: I1 [0-3], I2 [0-5], etc. (tooltip con descripción completa).
- **Columnas fijas**: Estudiante, Total obt., Total máx., % logro.
- **Encabezado fijo** al hacer scroll vertical.
- **Columna estudiante fija** al hacer scroll horizontal.

## 3. Comportamiento

- **Guardado masivo**: botón "Guardar todo" envía todos los puntajes.
- **Cálculos en tiempo real**: Total obtenido y % logro se actualizan al escribir.
- **Validación frontend**: celdas fuera de rango se marcan en rojo.
- **Guardado parcial**: celdas vacías se permiten (NULL en BD).

## 4. Casos de prueba obligatorios

### Caso A: Total 14, % 87.5
- Actividad con indicadores máximos 3, 5, 3, 5 (total 16).
- Estudiante con puntajes 3, 4, 2, 5.
- Verificar: Total obt. = 14, % logro = 87.5%.

### Caso B: Rechazar 4 en indicador 0-3
- Indicador con escala 0-3.
- Ingresar 4 → debe rechazarse (mensaje de error o celda en rojo).

### Caso C: Rechazar 0 en indicador 1-5
- Indicador con escala 1-5.
- Ingresar 0 → debe rechazarse.

### Caso D: Guardado parcial
- Dejar algunas celdas vacías.
- Guardar → debe permitirse.
- Recargar → las vacías siguen vacías, las llenas guardadas.

### Caso E: Docente no autorizado
- Con un docente que no es el asignado, acceder a `/docente/actividad/<id>/calificar/` de otra asignación.
- Debe rechazar con mensaje de error.

## 5. Archivos modificados/creados (Fase 3)

- `libro_docente/services.py` – `guardar_puntajes_masivo()`
- `libro_docente/views.py` – `actividad_calificar_view` (implementación completa)
- `libro_docente/templates/libro_docente/calificacion.html` – grilla de calificación
