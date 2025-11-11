# catalogos/admin.py
from django.contrib import admin
from django.db.models import Prefetch
from django.utils.html import format_html_join
from .models import (
    Provincia, Canton, Distrito,
    Nivel, TipoIdentificacion, Nacionalidad, Adecuacion,
    Modalidad, Especialidad, SubArea, Sexo,
    EstadoCivil, Parentesco, Escolaridad, Ocupacion,
    Seccion, Subgrupo, CursoLectivo, SubAreaInstitucion
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

@admin.register(CursoLectivo)
class CursoLectivoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'anio', 'fecha_inicio', 'fecha_fin', 'estado_activo', 'estado_matricular')
    list_filter = ('anio', 'activo', 'matricular')
    search_fields = ('nombre', 'anio')
    ordering = ('-anio',)
    
    fields = ('anio', 'nombre', 'fecha_inicio', 'fecha_fin', 'activo', 'matricular')
    
    @admin.display(description="Nombre del curso", ordering='nombre')
    def nombre_completo(self, obj):
        return str(obj)  # Usa el __str__ que incluye las etiquetas
    
    @admin.display(description="Curso Activo", boolean=True, ordering='activo')
    def estado_activo(self, obj):
        return obj.activo
    
    @admin.display(description="Matriculando", boolean=True, ordering='matricular')
    def estado_matricular(self, obj):
        return obj.matricular
    
    def save_model(self, request, obj, form, change):
        """
        Al guardar, si se marca como activo o matricular, 
        automáticamente desactiva los demás (esto ya está en el modelo).
        Mostrar mensaje informativo.
        """
        from django.contrib import messages
        
        was_activo = False
        was_matricular = False
        
        if change:
            old_obj = CursoLectivo.objects.get(pk=obj.pk)
            was_activo = old_obj.activo
            was_matricular = old_obj.matricular
        
        super().save_model(request, obj, form, change)
        
        # Mensajes informativos
        if obj.activo and not was_activo:
            messages.success(request, f"✅ {obj.nombre} ahora es el curso lectivo ACTIVO. Los demás cursos fueron desactivados automáticamente.")
        
        if obj.matricular and not was_matricular:
            messages.success(request, f"📚 {obj.nombre} ahora es el curso para MATRÍCULA. Los demás cursos fueron desmarcados automáticamente.")


@admin.register(SubAreaInstitucion)
class SubAreaInstitucionAdmin(admin.ModelAdmin):
    list_display = ('institucion', 'subarea', 'activa')
    list_filter = ('institucion', 'subarea__especialidad__modalidad', 'activa')
    search_fields = ('institucion__nombre', 'subarea__nombre')
    ordering = ('institucion__nombre', 'subarea__nombre')
    autocomplete_fields = ('institucion', 'subarea')

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ('institucion', 'subarea', 'activa')
        return ('subarea', 'activa')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'institucion' and not request.user.is_superuser:
            from core.models import Institucion
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                kwargs['queryset'] = Institucion.objects.filter(id=institucion_id)
                kwargs['initial'] = institucion_id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                obj.institucion_id = institucion_id
        super().save_model(request, obj, form, change)