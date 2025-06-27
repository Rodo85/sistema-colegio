from django.contrib import admin
from django.contrib.admin import RelatedOnlyFieldListFilter
from core.mixins import InstitucionScopedAdmin
from .models import Seccion, Subgrupo, Profesor, Clase

class SubgrupoInline(admin.TabularInline):
    model = Subgrupo
    extra = 0

class ClaseInline(admin.TabularInline):
    model = Clase
    extra = 0
    autocomplete_fields = ("materia", "subgrupo")

@admin.register(Seccion)
class SeccionAdmin(InstitucionScopedAdmin):
    list_display = ("codigo", "institucion")
    ordering     = ("nivel__numero", "numero")
    inlines      = [SubgrupoInline]

@admin.register(Subgrupo)
class SubgrupoAdmin(InstitucionScopedAdmin):
    list_display      = ("codigo", "seccion")
    list_filter       = ("seccion__nivel__numero",)
    search_fields     = ("codigo",)

@admin.register(Profesor)
class ProfesorAdmin(InstitucionScopedAdmin):
    list_display      = ("identificacion", "primer_apellido", "segundo_apellido", "nombres", "correo", "telefono")
    search_fields     = ("identificacion", "primer_apellido", "segundo_apellido", "nombres")
    inlines           = [ClaseInline]

@admin.register(Clase)
class ClaseAdmin(InstitucionScopedAdmin):
    change_form_template = "admin/config_institucional/clase/change_form.html"
    list_display         = ("materia", "subgrupo", "profesor", "periodo")
    list_filter = (
        "periodo",
        "materia__tipo",
        (
            "subgrupo",
            RelatedOnlyFieldListFilter,
        ),
    )
    autocomplete_fields  = ("profesor", "materia", "subgrupo")

