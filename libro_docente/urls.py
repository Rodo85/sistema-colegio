from django.urls import path

from .views import (
    actividad_calificar_view,
    actividad_copiar_a_grupos_view,
    actividad_create_view,
    actividad_delete_view,
    actividad_duplicar_view,
    actividad_edit_view,
    actividad_list_view,
    prueba_lista_ejecucion_view,
    asignacion_delete_view,
    asignacion_estudiantes_excel_view,
    asignacion_onboarding_view,
    asistencia_view,
    detalle_estudiante_view,
    estudiante_consulta_view,
    estudiantes_config_view,
    home_docente,
    resumen_estudiante_detalle_view,
    resumen_general_export_csv,
    resumen_general_export_xlsx,
    resumen_evaluacion_view,
    resumen_view,
)

app_name = "libro_docente"

urlpatterns = [
    path("hoy/", home_docente, name="home"),
    path("asignacion/onboarding/", asignacion_onboarding_view, name="asignacion_onboarding"),
    path("asignacion/<int:asignacion_id>/estudiantes-excel/", asignacion_estudiantes_excel_view, name="asignacion_estudiantes_excel"),
    path("asignacion/<int:asignacion_id>/eliminar/", asignacion_delete_view, name="asignacion_delete"),
    path("asignacion/<int:asignacion_id>/estudiantes-config/", estudiantes_config_view, name="estudiantes_config"),
    path("asistencia/<int:asignacion_id>/", asistencia_view, name="asistencia"),
    path("asistencia/<int:asignacion_id>/resumen/", resumen_view, name="resumen"),
    path(
        "asistencia/<int:asignacion_id>/resumen/estudiante/<int:estudiante_id>/",
        detalle_estudiante_view,
        name="detalle_estudiante",
    ),
    path(
        "asistencia/<int:asignacion_id>/resumen/estudiante/<int:estudiante_id>/consulta/",
        estudiante_consulta_view,
        name="estudiante_consulta",
    ),
    # Evaluación por indicadores (TAREAS / COTIDIANOS)
    path("asignacion/<int:asignacion_id>/actividades/", actividad_list_view, name="actividad_list"),
    path("asignacion/<int:asignacion_id>/actividad/nueva/", actividad_create_view, name="actividad_create"),
    path("actividad/<int:actividad_id>/editar/", actividad_edit_view, name="actividad_edit"),
    path("actividad/<int:actividad_id>/eliminar/", actividad_delete_view, name="actividad_delete"),
    path("actividad/<int:actividad_id>/prueba-lista-ejecucion/", prueba_lista_ejecucion_view, name="prueba_lista_ejecucion"),
    path("actividad/<int:actividad_id>/duplicar/", actividad_duplicar_view, name="actividad_duplicar"),
    path("actividad/<int:actividad_id>/copiar-a-grupos/", actividad_copiar_a_grupos_view, name="actividad_copiar_a_grupos"),
    path("actividad/<int:actividad_id>/calificar/", actividad_calificar_view, name="actividad_calificar"),
    path("asignacion/<int:asignacion_id>/resumen-evaluacion/", resumen_evaluacion_view, name="resumen_evaluacion"),
    path("asignacion/<int:asignacion_id>/resumen-evaluacion/export/xlsx/", resumen_general_export_xlsx, name="resumen_general_export_xlsx"),
    path("asignacion/<int:asignacion_id>/resumen-evaluacion/export/csv/", resumen_general_export_csv, name="resumen_general_export_csv"),
    path(
        "asignacion/<int:asignacion_id>/resumen-evaluacion/estudiante/<int:estudiante_id>/",
        resumen_estudiante_detalle_view,
        name="resumen_estudiante_detalle",
    ),
]
