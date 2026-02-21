from django.urls import path

from .views import (
    almuerzo_comedor,
    gestionar_tiquetes,
    imprimir_tiquetes,
    registrar_beca_comedor,
    reportes_comedor,
    toggle_tiquete,
)

app_name = "comedor"

urlpatterns = [
    path("registrar-beca/", registrar_beca_comedor, name="registrar_beca"),
    path("almuerzo/", almuerzo_comedor, name="almuerzo"),
    path("reportes/", reportes_comedor, name="reportes"),
    path("tiquetes/", gestionar_tiquetes, name="tiquetes"),
    path("tiquetes/<int:tiquete_id>/toggle/", toggle_tiquete, name="toggle_tiquete"),
    path("tiquetes/imprimir/", imprimir_tiquetes, name="imprimir_tiquetes"),
]
