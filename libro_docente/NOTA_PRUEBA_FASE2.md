# Nota: Cómo probar la Fase 2 manualmente

## 1. Acceso a actividades

- Desde **Mis asignaciones** (`/docente/hoy/`): los chips TAREAS y COTIDIANO (si existen en el esquema) llevan a la lista de actividades.
- URL directa: `/docente/asignacion/<id>/actividades/`

## 2. Lista de actividades

- Filtros: período, tipo (Tareas / Cotidianos / Todos).
- Botones: "+ Nueva tarea", "+ Nuevo cotidiano" (cuando hay período seleccionado).
- Columnas: Fecha/Período, Tipo, Título, Grupo, Materia, Indicadores, Total máx., Estado, Acciones.
- Acciones por fila: Editar, Duplicar, Calificar (placeholder), Eliminar.
- "Ver resumen" en el banner: placeholder para Fase 3.

## 3. Crear actividad

1. Seleccionar período y tipo.
2. Clic en "Nueva tarea" o "Nuevo cotidiano".
3. Completar: título, descripción, fechas, estado.
4. Guardar → redirige a editar para agregar indicadores.

## 4. Editar actividad e indicadores

1. Clic en "Editar" en una actividad.
2. Modificar datos de la actividad.
3. En la sección Indicadores: agregar filas (orden, descripción, escala_min, escala_max, activo).
4. Marcar "Eliminar" para quitar un indicador.
5. El badge "Total máximo" se actualiza en tiempo real al cambiar escala_max.
6. Guardar actividad e indicadores.

## 5. Casos de prueba funcionales

### Caso 1: Total máximo = 16
- Crear actividad con 4 indicadores: 0-3, 0-5, 0-3, 0-5.
- Verificar que "Total máximo" muestre 16.

### Caso 2: Editar indicador
- Editar un indicador (por ejemplo, cambiar escala_max de 5 a 4).
- Verificar que el total máximo se actualice.

### Caso 3: Duplicar sin puntajes
- Crear actividad con indicadores y puntajes (desde admin).
- Duplicar la actividad.
- Verificar que la copia tenga indicadores pero NO puntajes.
- Título debe ser "Copia – [título original]".

### Caso 4: Docente no autorizado
- Con un docente que no es el asignado, intentar editar una actividad ajena (URL directa).
- Debe rechazar con mensaje de error.

## 6. Validaciones

- **Frontend**: escala_max >= escala_min (al enviar).
- **Backend**: mismas validaciones en forms y models.
- Descripción de indicador: obligatoria (modelo).

## 7. Archivos modificados/creados (Fase 2)

- `libro_docente/services.py` – función `duplicar_actividad`
- `libro_docente/forms.py` – `IndicadorActividadFormSet`
- `libro_docente/views.py` – vistas: delete, duplicar, calificar (placeholder), resumen_evaluacion (placeholder); edit con formset
- `libro_docente/urls.py` – rutas nuevas
- `libro_docente/templates/libro_docente/actividad_list.html` – columnas y acciones
- `libro_docente/templates/libro_docente/actividad_form.html` – formset de indicadores, total máximo en tiempo real
- `libro_docente/templates/libro_docente/actividad_confirm_delete.html` – confirmación de eliminación
- `libro_docente/templates/libro_docente/actividad_placeholder.html` – pantallas placeholder
- `libro_docente/templates/libro_docente/hoy.html` – chips TAREAS/COTIDIANO activos
