from django.urls import path
from .views import marcar_ingreso


urlpatterns = [
    path("marcar/", marcar_ingreso, name="marcar_ingreso"),
]






