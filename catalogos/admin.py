from django.contrib import admin
from .models import (
    Provincia, Canton, Distrito,
    Nivel, TipoIdentificacion, Nacionalidad, Adecuacion,
    Modalidad, Especialidad, SubArea, Materia,
)

# ── Registramos los catálogos globales ────────────────────
#admin.site.register([Provincia, Canton, Distrito])

@admin.register(Nivel)
class NivelAdmin(admin.ModelAdmin):
    list_display = ("numero", "nombre")
    ordering     = ("numero",)

@admin.register(TipoIdentificacion)
class TipoIdentificacionAdmin(admin.ModelAdmin):
    list_display = ("nombre",)

@admin.register(Nacionalidad)
class NacionalidadAdmin(admin.ModelAdmin):
    list_display = ("nombre",)

@admin.register(Adecuacion)
class AdecuacionAdmin(admin.ModelAdmin):
    list_display = ("descripcion",)

@admin.register(Modalidad)
class ModalidadAdmin(admin.ModelAdmin):
    list_display = ("nombre",)

@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    list_display  = ("modalidad", "nombre")
    list_filter   = ("modalidad",)
    search_fields = ("nombre",)

@admin.register(SubArea)
class SubAreaAdmin(admin.ModelAdmin):
    list_display  = ("especialidad", "nombre")
    list_filter   = ("especialidad__modalidad",)
    search_fields = ("nombre",)

@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display  = ("nombre", "tipo", "subarea")
    list_filter   = ("tipo", "subarea__especialidad")
    search_fields = ("nombre",)