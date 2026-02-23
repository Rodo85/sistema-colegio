from django.urls import path

from .views import asistencia_view, home_docente, resumen_view

app_name = "libro_docente"

urlpatterns = [
    path("hoy/", home_docente, name="home"),
    path("asistencia/<int:asignacion_id>/", asistencia_view, name="asistencia"),
    path("asistencia/<int:asignacion_id>/resumen/", resumen_view, name="resumen"),
]
