from django.urls import path

from .views import (
    asignacion_estudiantes_view,
    actividad_calificar_view,
    actividad_copiar_a_grupos_view,
    actividad_create_view,
    actividad_delete_view,
    actividad_duplicar_view,
    actividad_edit_view,
    actividad_list_view,
    asistencia_view,
    detalle_estudiante_view,
    home_docente,
    resumen_estudiante_detalle_view,
    resumen_evaluacion_view,
    resumen_view,
)

app_name = "libro_docente"

urlpatterns = [
    path("hoy/", home_docente, name="home"),
    path(
        "asignacion/<int:asignacion_id>/estudiantes/",
        asignacion_estudiantes_view,
        name="asignacion_estudiantes",
    ),
    path("asistencia/<int:asignacion_id>/", asistencia_view, name="asistencia"),
    path("asistencia/<int:asignacion_id>/resumen/", resumen_view, name="resumen"),
    path(
        "asistencia/<int:asignacion_id>/resumen/estudiante/<int:estudiante_id>/",
        detalle_estudiante_view,
        name="detalle_estudiante",
    ),
    # Evaluación por indicadores (TAREAS / COTIDIANOS)
    path("asignacion/<int:asignacion_id>/actividades/", actividad_list_view, name="actividad_list"),
    path("asignacion/<int:asignacion_id>/actividad/nueva/", actividad_create_view, name="actividad_create"),
    path("actividad/<int:actividad_id>/editar/", actividad_edit_view, name="actividad_edit"),
    path("actividad/<int:actividad_id>/eliminar/", actividad_delete_view, name="actividad_delete"),
    path("actividad/<int:actividad_id>/duplicar/", actividad_duplicar_view, name="actividad_duplicar"),
    path("actividad/<int:actividad_id>/copiar-a-grupos/", actividad_copiar_a_grupos_view, name="actividad_copiar_a_grupos"),
    path("actividad/<int:actividad_id>/calificar/", actividad_calificar_view, name="actividad_calificar"),
    path("asignacion/<int:asignacion_id>/resumen-evaluacion/", resumen_evaluacion_view, name="resumen_evaluacion"),
    path(
        "asignacion/<int:asignacion_id>/resumen-evaluacion/estudiante/<int:estudiante_id>/",
        resumen_estudiante_detalle_view,
        name="resumen_estudiante_detalle",
    ),
]
