from django.contrib import admin
from django.utils.html import format_html

from core.mixins import InstitucionScopedAdmin

from .models import (
    ComponenteEval,
    DocenteAsignacion,
    EsquemaEval,
    EsquemaEvalComponente,
    Periodo,
    PeriodoCursoLectivo,
    SubareaCursoLectivo,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Componentes de evaluación (catálogo global – solo superusuario)
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(ComponenteEval)
class ComponenteEvalAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
    ordering = ("nombre",)


# ─────────────────────────────────────────────────────────────────────────────
#  Esquemas de evaluación (global – solo superusuario)
# ─────────────────────────────────────────────────────────────────────────────

class EsquemaEvalComponenteInline(admin.TabularInline):
    model = EsquemaEvalComponente
    extra = 1
    fields = ("componente", "porcentaje", "reglas_json")
    autocomplete_fields = ("componente",)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.locked:
            return ("componente", "porcentaje", "reglas_json")
        return ()

    def has_add_permission(self, request, obj=None):
        if obj and obj.locked:
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.locked:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(EsquemaEval)
class EsquemaEvalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "modalidad", "especialidad", "total_pct_display", "locked", "activo")
    list_filter = ("tipo", "locked", "activo", "modalidad")
    search_fields = ("nombre",)
    inlines = [EsquemaEvalComponenteInline]
    readonly_fields = ("created_at", "updated_at", "total_pct_display")
    fieldsets = (
        (None, {"fields": ("nombre", "tipo", "activo", "locked")}),
        ("Aplicabilidad (opcional)", {"fields": ("modalidad", "especialidad"), "classes": ("collapse",)}),
        ("Vigencia", {"fields": ("vigente_desde", "vigente_hasta"), "classes": ("collapse",)}),
        ("Auditoría", {"fields": ("created_at", "updated_at", "total_pct_display"), "classes": ("collapse",)}),
    )

    @admin.display(description="Total %")
    def total_pct_display(self, obj):
        if not obj.pk:
            return "—"
        total = obj.get_total_porcentaje()
        color = "green" if total == 100 else "red"
        return format_html('<strong style="color:{}">{} %</strong>', color, total)


@admin.register(EsquemaEvalComponente)
class EsquemaEvalComponenteAdmin(admin.ModelAdmin):
    list_display = ("esquema", "componente", "porcentaje")
    list_filter = ("esquema__tipo", "componente")
    search_fields = ("esquema__nombre", "componente__nombre")


# ─────────────────────────────────────────────────────────────────────────────
#  Períodos (catálogo global – solo superusuario)
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ("numero", "nombre")
    ordering = ("numero",)


# ─────────────────────────────────────────────────────────────────────────────
#  Subáreas por Curso Lectivo (institucional)
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(SubareaCursoLectivo)
class SubareaCursoLectivoAdmin(InstitucionScopedAdmin):
    list_display = (
        "subarea",
        "tipo_subarea",
        "curso_lectivo",
        "institucion",
        "eval_scheme",
        "activa",
    )
    list_filter = ("institucion", "curso_lectivo", "activa", "subarea__es_academica")
    search_fields = ("subarea__nombre",)
    autocomplete_fields = ("subarea", "eval_scheme")

    @admin.display(description="Tipo", ordering="subarea__es_academica")
    def tipo_subarea(self, obj):
        if obj.subarea.es_academica:
            return format_html('<span style="color:#1a6eb5;">Académica</span>')
        return format_html('<span style="color:#7c3aed;">Técnica</span>')


# ─────────────────────────────────────────────────────────────────────────────
#  Períodos por Curso Lectivo (institucional)
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(PeriodoCursoLectivo)
class PeriodoCursoLectivoAdmin(InstitucionScopedAdmin):
    list_display = ("periodo", "curso_lectivo", "institucion", "fecha_inicio", "fecha_fin", "activo")
    list_filter = ("institucion", "curso_lectivo", "activo")
    search_fields = ("periodo__nombre",)


# ─────────────────────────────────────────────────────────────────────────────
#  Asignaciones Docentes (institucional)
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(DocenteAsignacion)
class DocenteAsignacionAdmin(InstitucionScopedAdmin):
    list_display = (
        "docente",
        "subarea_nombre",
        "tipo_materia",
        "grupo_display",
        "curso_lectivo",
        "eval_scheme_snapshot",
        "activo",
    )
    list_filter = (
        "subarea_curso__institucion",
        "curso_lectivo",
        "activo",
        "subarea_curso__subarea__es_academica",
    )
    search_fields = (
        "docente__usuario__first_name",
        "docente__usuario__last_name",
        "subarea_curso__subarea__nombre",
    )
    autocomplete_fields = ("docente", "subarea_curso", "seccion", "subgrupo")
    readonly_fields = ("eval_scheme_snapshot", "created_at")

    @admin.display(description="Materia")
    def subarea_nombre(self, obj):
        return obj.subarea_curso.subarea.nombre

    @admin.display(description="Tipo")
    def tipo_materia(self, obj):
        if obj.subarea_curso.subarea.es_academica:
            return format_html('<span style="color:#1a6eb5;">Académica</span>')
        return format_html('<span style="color:#7c3aed;">Técnica</span>')

    @admin.display(description="Sección / Subgrupo")
    def grupo_display(self, obj):
        if obj.seccion_id:
            return f"Secc. {obj.seccion}"
        if obj.subgrupo_id:
            return f"Subgr. {obj.subgrupo}"
        return "—"
