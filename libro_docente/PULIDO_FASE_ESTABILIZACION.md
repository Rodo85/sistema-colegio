# Fase de pulido / estabilización – Módulo de evaluación por indicadores

## 1. Hallazgos

### 1.1 Permisos y multiinstitución ✅
- **listar (actividad_list_view)**: Usa `_obtener_asignacion_con_permiso` + validación `inst_activa`. Docente solo ve sus asignaciones; superadmin ve todas.
- **crear (actividad_create_view)**: Misma validación. ✅
- **editar (actividad_edit_view)**: Usa `puede_usuario_editar_actividad` + `actividad_pertenece_a_institucion`. ✅
- **eliminar (actividad_delete_view)**: Misma validación. Requiere POST para confirmar. ✅
- **duplicar (actividad_duplicar_view)**: Misma validación. GET con confirmación JS añadida. ✅
- **calificar (actividad_calificar_view)**: Misma validación. ✅
- **ver resumen (resumen_evaluacion_view, resumen_estudiante_detalle_view)**: Usa `_obtener_asignacion_con_permiso` + validación institución. ✅

**Conclusión**: Todas las rutas validan permisos e institución. Docente normal no puede operar otra institución ni asignaciones ajenas.

### 1.2 Validaciones de datos ✅
- **escala_max >= escala_min**: Modelo tiene `CheckConstraint`, formulario `IndicadorActividadForm.clean()`, modelo `IndicadorActividad.clean()`. ✅
- **Rangos de puntajes**: `validar_puntaje_en_rango` en services, `PuntajeIndicador.clean()`, `guardar_puntajes_masivo` valida antes de guardar. ✅
- **Integridad indicador-actividad**: `guardar_puntajes_masivo` ahora filtra `IndicadorActividad.objects.filter(id__in=..., actividad=actividad)`. ✅
- **Integridad estudiante-grupo**: `_get_estudiantes(asignacion)` devuelve solo estudiantes del grupo; `guardar_puntajes_masivo` recibe `estudiante_ids` de ahí. ✅
- **Duplicados puntaje**: `PuntajeIndicador` tiene `UniqueConstraint(indicador, estudiante)`. `update_or_create` evita duplicados. ✅

### 1.3 Cálculos consistentes ✅
- Backend usa `Decimal` en services.
- Constante `DECIMAL_PLACES = 2` y helper `_redondear()` añadidos para uso futuro.
- Plantillas usan `floatformat:1` o `floatformat:2` según contexto.
- Grilla de calificación: total obtenido y % logro ahora se calculan en backend y se muestran correctamente al cargar. ✅

### 1.4 UX/usabilidad ✅
- Mensajes: éxito, error e info (ej. "No hubo cambios que guardar") mejorados.
- Confirmación de eliminación: ya existía con formulario POST y CSRF.
- Confirmación de duplicar: añadida con `onclick="return confirm(...)"`.
- Grilla de calificación: muestra total obtenido y % logro reales al cargar (antes mostraba 0).

### 1.5 Rendimiento ✅
- **actividad_list**: Eliminado N+1. Antes: `calcular_total_maximo_actividad(a)` y `a.indicadores.count()` por actividad. Ahora: usa `prefetch_related("indicadores")` y calcula en memoria.
- **calcular_resumen_evaluacion_completo**: Optimizado. Antes: 2×N llamadas a `calcular_resumen_componente_estudiante` (N = estudiantes), cada una con múltiples queries. Ahora: prefetch actividades e indicadores, una query de puntajes por tipo de componente.

### 1.6 Auditoría
- `ActividadEvaluacion` ya tiene `created_by` y `updated_at`.
- **Pendiente sugerido**: Añadir `updated_by` a `ActividadEvaluacion` (requiere migración).

---

## 2. Mejoras aplicadas

| Área | Mejora |
|------|--------|
| Validaciones | `guardar_puntajes_masivo` filtra indicadores por `actividad` (integridad) |
| Cálculos | Constante `DECIMAL_PLACES` y helper `_redondear()` en services |
| UX | Mensaje "No hubo cambios que guardar" al guardar calificación sin cambios |
| UX | Confirmación JS al duplicar actividad |
| UX | Grilla calificación: total obtenido y % logro correctos al cargar |
| Rendimiento | `actividad_list`: uso de prefetch para evitar N+1 |
| Rendimiento | `calcular_resumen_evaluacion_completo`: optimización con prefetch y query única de puntajes |

---

## 3. Archivos modificados

| Archivo | Cambios |
|---------|---------|
| `libro_docente/services.py` | Validación indicador-actividad en `guardar_puntajes_masivo`; `DECIMAL_PLACES`, `_redondear()`; optimización `calcular_resumen_evaluacion_completo` |
| `libro_docente/views.py` | `actividad_list`: cálculo con prefetch; `actividad_calificar`: `total_obtenido`, `porcentaje_logro` por fila; mensaje "No hubo cambios" |
| `libro_docente/templates/libro_docente/actividad_list.html` | Confirmación JS en enlace Duplicar |
| `libro_docente/templates/libro_docente/calificacion.html` | Valores iniciales de total obtenido y % logro; JS con `toFixed(2)` para consistencia |

---

## 4. Casos de prueba manual recomendados

### Permisos
1. Docente A: ver solo sus asignaciones; no acceder a asignación de Docente B.
2. Docente: no acceder a actividad de otra institución (cambiar institución activa si aplica).
3. Superadmin: acceder a cualquier asignación/actividad.

### Validaciones
4. Indicador: escala_max < escala_min → error en formulario.
5. Calificación: puntaje fuera de rango → mensaje de error al guardar.
6. Calificación: valor no numérico → mensaje de error.

### Cálculos
7. Grilla calificación: al cargar, total obtenido y % logro coinciden con puntajes guardados.
8. Resumen: aporte = (porcentaje_logro/100) × porcentaje_componente.

### UX
9. Eliminar: formulario de confirmación, solo elimina con POST.
10. Duplicar: confirmación JS antes de duplicar.
11. Calificar: guardar sin cambios → mensaje "No hubo cambios que guardar".

### Rendimiento
12. Lista actividades: con 20+ actividades, verificar que no haya lentitud (antes N+1).
13. Resumen evaluación: con 30+ estudiantes, verificar que cargue rápido.

---

## 5. Pendientes sugeridos (fase futura)

| Prioridad | Pendiente |
|-----------|-----------|
| Media | Añadir `updated_by` a `ActividadEvaluacion` (migración) |
| Baja | Duplicar actividad: requerir POST en lugar de GET (evitar disparo por crawlers) |
| Baja | Indicador de carga al guardar calificación (spinner o deshabilitar botón) |
| Baja | Paginación en lista de actividades si hay muchas |
| Opcional | Registrar fecha de última calificación por actividad |
