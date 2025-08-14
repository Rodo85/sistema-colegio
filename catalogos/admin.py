# catalogos/admin.py
from django.contrib import admin
from django.db.models import Prefetch
from django.utils.html import format_html_join
from .models import (
    Provincia, Canton, Distrito,
    Nivel, TipoIdentificacion, Nacionalidad, Adecuacion,
    Modalidad, Especialidad, SubArea, Sexo,
    EstadoCivil, Parentesco, Escolaridad, Ocupacion,
    Seccion, Subgrupo
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


# ═══════════════════════════════════════════════════════════════════
#                    SECCIONES Y SUBGRUPOS GLOBALES
# ═══════════════════════════════════════════════════════════════════

class SubgrupoInline(admin.TabularInline):
    model = Subgrupo
    extra = 0
    fields = ("letra",)

def _nivel_num(obj):
    """Obtiene el número del nivel de forma robusta (campo 'numero' o el FK id)."""
    return getattr(obj.nivel, "numero", obj.nivel_id)

@admin.register(Seccion)
class SeccionAdmin(admin.ModelAdmin):
    # ==> Cambie las columnas para que sí aparezcan 7-1 y 7-1A, 7-1B...
    list_display = ("codigo", "subgrupos_codigos")
    list_display_links = ("codigo",)
    list_filter = ("nivel",)
    search_fields = ("nivel__nombre", "numero")
    ordering = ("nivel__numero", "numero")  # si su modelo Nivel no tiene 'numero', use "nivel_id"

    # Si usa inlines, puede dejarlos:
    # inlines = [SubgrupoInline]

    @admin.display(description="Sección", ordering=("nivel__numero", "numero"))
    def codigo(self, obj):
        return f"{_nivel_num(obj)}-{obj.numero}"

    @admin.display(description="Subgrupos")
    def subgrupos_codigos(self, obj):
        # Genera 7-1A, 7-1B, ...; sepárelos por coma o espacio según prefiera
        base = f"{_nivel_num(obj)}-{obj.numero}"
        items = [f"{base}{sg.letra}" for sg in obj.subgrupos.all()]
        # return ", ".join(items) or "-"  # <- si prefiere texto plano
        return format_html_join(", ", "{}", ((item,) for item in items)) or "-"

    def get_queryset(self, request):
        # Optimiza: trae nivel y subgrupos ordenados por letra
        qs = super().get_queryset(request)
        return qs.select_related("nivel").prefetch_related(
            Prefetch("subgrupos", queryset=Subgrupo.objects.only("id", "letra", "seccion_id").order_by("letra"))
        )



@admin.register(Subgrupo)
class SubgrupoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "letra")
    ordering = ("seccion__nivel__numero", "seccion__numero", "letra")
    search_fields = ("seccion__nivel__nombre", "seccion__numero", "letra")

    @admin.display(description="Subgrupo", ordering=("seccion__nivel__numero", "seccion__numero", "letra"))
    def codigo(self, obj):
        return f"{_nivel_num(obj.seccion)}-{obj.seccion.numero}{obj.letra}"