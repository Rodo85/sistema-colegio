# Nota: Cómo probar la Fase 1 manualmente

## 1. Aplicar migraciones

```bash
python manage.py migrate libro_docente
```

## 2. Probar desde Django Admin

1. Iniciar sesión como superusuario o docente con `libro_docente.access_libro_docente`.
2. Ir a **Libro del Docente** → **Actividades de evaluación**.
3. Crear una actividad:
   - Asignación docente
   - Institución, curso lectivo, período
   - Tipo: TAREA o COTIDIANO
   - Título, estado (BORRADOR/ACTIVA/CERRADA)
4. En la misma pantalla, agregar indicadores (inline):
   - Orden, descripción, escala_min, escala_max
5. Guardar.

## 3. Probar desde vistas del libro del docente

1. Ir a `/docente/hoy/` (Mis asignaciones).
2. La URL de actividades es: `/docente/asignacion/<id>/actividades/`
3. Seleccionar un período y tipo (Tareas/Cotidianos).
4. Crear nueva actividad con "Nueva tarea" o "Nuevo cotidiano".
5. Editar actividad y agregar indicadores desde el admin.

## 4. Casos de prueba mínimos

### Caso 1: Total máximo
- Crear actividad con 4 indicadores: 0-3, 0-5, 0-3, 0-5.
- Verificar: `calcular_total_maximo_actividad(actividad)` = 16.

### Caso 2: Porcentaje de logro
- En la misma actividad, asignar puntajes 3, 4, 2, 5 a un estudiante.
- Verificar: total_obtenido = 14, porcentaje_logro = 87.5%.

### Caso 3: Validación de rango
- Intentar guardar puntaje 4 en un indicador 0-3.
- Debe rechazarse (ValidationError o ValueError).

## 5. Ejecutar tests

```bash
python manage.py test libro_docente.tests.EvaluacionIndicadoresTests
```

## 6. Servicios disponibles

- `calcular_total_maximo_actividad(actividad)`
- `calcular_total_obtenido_estudiante(actividad, estudiante_id)`
- `calcular_porcentaje_logro(actividad, estudiante_id)`
- `validar_puntaje_en_rango(indicador, valor)`
- `guardar_o_actualizar_puntaje(indicador_id, estudiante_id, puntaje_obtenido, observacion)`
