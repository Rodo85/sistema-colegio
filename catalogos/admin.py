from django.contrib import admin
from .models import (
    TipoIdentificacion, Nacionalidad, Adecuacion,
    Nivel, Seccion, Subgrupo,
    Materia, Profesor, Clase, Especialidad
)

# ──────────────────────────
# 1.  Catálogos “simples”
# ──────────────────────────
admin.site.register([
    TipoIdentificacion,
    Nacionalidad,
    Adecuacion,
])

# ──────────────────────────
# 2.  Inlines y EspecialidadAdmin
# ──────────────────────────
@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        from .forms import EspecialidadForm  # Importación local
        kwargs['form'] = EspecialidadForm
        return super().get_form(request, obj, **kwargs)

    list_display  = ("nombre", "año")
    list_filter   = ("año",)
    search_fields = ("nombre",)


class SubgrupoInline(admin.TabularInline):
    model = Subgrupo
    extra = 0


class ClaseInline(admin.TabularInline):
    model = Clase
    extra = 0
    autocomplete_fields = ("materia", "subgrupo")


# ──────────────────────────
# 3.  ModelAdmin con configuración
# ──────────────────────────
@admin.register(Nivel)
class NivelAdmin(admin.ModelAdmin):
    list_display = ("numero", "nombre")
    ordering     = ("numero",)


@admin.register(Seccion)
class SeccionAdmin(admin.ModelAdmin):
    list_display = ("codigo",)
    ordering     = ("nivel__numero", "numero")
    inlines      = [SubgrupoInline]


@admin.register(Subgrupo)
class SubgrupoAdmin(admin.ModelAdmin):
    list_display  = ("codigo", "seccion")
    list_filter   = ("seccion__nivel__numero",)
    search_fields = ("seccion__nivel__numero", "seccion__numero", "letra")


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display    = ("nombre", "tipo")
    list_filter     = ("tipo",)
    search_fields   = ("nombre",)


@admin.register(Profesor)
class ProfesorAdmin(admin.ModelAdmin):
    list_display  = ("identificacion", "primer_apellido", "nombres", "correo")
    search_fields = ("identificacion", "primer_apellido", "segundo_apellido", "nombres")
    inlines       = [ClaseInline]


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display         = ("materia", "subgrupo", "profesor", "periodo")
    list_filter          = ("periodo", "materia__tipo", "subgrupo__seccion__nivel__numero")
    autocomplete_fields  = ("profesor", "materia", "subgrupo")
