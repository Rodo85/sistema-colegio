from django.contrib import admin

from core.mixins import InstitucionScopedAdmin

from .forms import ConfiguracionComedorForm
from .models import BecaComedor, ConfiguracionComedor, RegistroAlmuerzo


@admin.register(ConfiguracionComedor)
class ConfiguracionComedorAdmin(InstitucionScopedAdmin):
    form = ConfiguracionComedorForm
    list_display = ("institucion", "intervalo_horas_display")
    search_fields = ("institucion__nombre",)

    @admin.display(description="Intervalo (horas)")
    def intervalo_horas_display(self, obj):
        horas = round(obj.intervalo_minutos / 60, 1)
        return f"{horas} h"


@admin.register(BecaComedor)
class BecaComedorAdmin(InstitucionScopedAdmin):
    list_display = (
        "estudiante",
        "institucion",
        "curso_lectivo",
        "activa",
        "fecha_asignacion",
    )
    list_filter = ("institucion", "curso_lectivo", "activa")
    search_fields = (
        "estudiante__identificacion",
        "estudiante__primer_apellido",
        "estudiante__segundo_apellido",
        "estudiante__nombres",
    )


@admin.register(RegistroAlmuerzo)
class RegistroAlmuerzoAdmin(InstitucionScopedAdmin):
    list_display = (
        "estudiante",
        "institucion",
        "curso_lectivo",
        "fecha",
        "fecha_hora",
    )
    list_filter = ("institucion", "curso_lectivo", "fecha")
    search_fields = (
        "estudiante__identificacion",
        "estudiante__primer_apellido",
        "estudiante__segundo_apellido",
        "estudiante__nombres",
    )

