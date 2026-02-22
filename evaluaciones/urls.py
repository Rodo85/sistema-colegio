from django.urls import path

from .views import (
    crear_asignacion,
    editar_asignacion,
    gestion_docentes,
    gestion_periodos,
    gestion_subareas,
    toggle_asignacion,
)

app_name = "evaluaciones"

urlpatterns = [
    path("subareas/", gestion_subareas, name="subareas"),
    path("periodos/", gestion_periodos, name="periodos"),
    path("docentes/", gestion_docentes, name="docentes"),
    path("docentes/nueva/", crear_asignacion, name="crear_asignacion"),
    path("docentes/<int:asignacion_id>/editar/", editar_asignacion, name="editar_asignacion"),
    path("docentes/<int:asignacion_id>/toggle/", toggle_asignacion, name="toggle_asignacion"),
]
