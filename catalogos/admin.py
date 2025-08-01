# catalogos/admin.py
from django.contrib import admin
from .models import (
    Provincia, Canton, Distrito,
    Nivel, TipoIdentificacion, Nacionalidad, Adecuacion,
    Modalidad, Especialidad, SubArea, Sexo,
    EstadoCivil, Parentesco, Escolaridad, Ocupacion
)

# ── Registrar modelos de ubicación con búsqueda para autocomplete_fields ──
@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)

@admin.register(Canton)
class CantonAdmin(admin.ModelAdmin):
    list_display = ("nombre", "provincia")
    list_filter  = ("provincia",)
    search_fields = ("nombre", "provincia__nombre")

@admin.register(Distrito)
class DistritoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "canton")
    list_filter  = ("canton",)
    search_fields = ("nombre", "canton__nombre")

# ── Registramos los catálogos globales ─────────────────────────────────
@admin.register(Nivel)
class NivelAdmin(admin.ModelAdmin):
    list_display = ("numero", "nombre")
    ordering     = ("numero",)
    search_fields = ("nombre",)

@admin.register(TipoIdentificacion)
class TipoIdentificacionAdmin(admin.ModelAdmin):
    list_display = ("nombre",)

@admin.register(Nacionalidad)
class NacionalidadAdmin(admin.ModelAdmin):
    list_display   = ("nombre",)
    search_fields  = ("nombre",)

@admin.register(Adecuacion)
class AdecuacionAdmin(admin.ModelAdmin):
    list_display = ("descripcion",)

@admin.register(Modalidad)
class ModalidadAdmin(admin.ModelAdmin):
    list_display  = ("nombre",)
    ordering      = ("nombre",)

@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    list_display   = ("modalidad", "nombre")
    list_filter    = ("modalidad",)
    search_fields  = ("nombre",)

@admin.register(SubArea)
class SubAreaAdmin(admin.ModelAdmin):
    list_display   = ("especialidad", "nombre")
    list_filter    = ("especialidad__modalidad",)
    search_fields  = ("nombre",)

@admin.register(Sexo)
class SexoAdmin(admin.ModelAdmin):
    list_display   = ("codigo", "nombre")
    search_fields  = ("codigo", "nombre")

@admin.register(EstadoCivil)
class EstadoCivilAdmin(admin.ModelAdmin):
    list_display = ("descripcion",)
    search_fields = ("descripcion",)
    ordering = ("descripcion",)

@admin.register(Parentesco)
class ParentescoAdmin(admin.ModelAdmin):
    list_display = ("descripcion",)
    search_fields = ("descripcion",)
    ordering = ("descripcion",)

@admin.register(Escolaridad)
class EscolaridadAdmin(admin.ModelAdmin):
    list_display   = ("descripcion",)
    search_fields  = ("descripcion",)

@admin.register(Ocupacion)
class OcupacionAdmin(admin.ModelAdmin):
    list_display   = ("descripcion",)
    search_fields  = ("descripcion",)