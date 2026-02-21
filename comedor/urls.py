from django.urls import path

from .views import almuerzo_comedor, registrar_beca_comedor, reportes_comedor

app_name = "comedor"

urlpatterns = [
    path("registrar-beca/", registrar_beca_comedor, name="registrar_beca"),
    path("almuerzo/", almuerzo_comedor, name="almuerzo"),
    path("reportes/", reportes_comedor, name="reportes"),
]

