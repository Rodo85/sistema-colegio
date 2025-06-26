from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import (
    TipoIdentificacion, Nacionalidad, Adecuacion,
    Especialidad, SubArea,
    Nivel, Seccion, Subgrupo,
    Materia, Profesor, Clase,
)
from .forms import EspecialidadForm

# ────────── MIXIN FILTRO POR COLEGIO ─────────────────────────
class InstitucionScopedAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(institucion_id=request.institucion_activa_id)

    def save_model(self, request, obj, form, change):
        if not change and hasattr(obj, "institucion_id") and not obj.institucion_id:
            obj.institucion_id = request.institucion_activa_id
        super().save_model(request, obj, form, change)

# ────────── CATÁLOGOS GLOBALES ───────────────────────────────
admin.site.register([TipoIdentificacion, Nacionalidad, Adecuacion, SubArea])

@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    form          = EspecialidadForm
    list_display  = ("nombre",)
    search_fields = ("nombre",)

@admin.register(Nivel)
class NivelAdmin(admin.ModelAdmin):
    list_display = ("numero", "nombre")
    ordering     = ("numero",)

@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display  = ("nombre", "tipo", "subarea")
    list_filter   = ("tipo",)
    search_fields = ("nombre",)

# ────────── MODELOS POR INSTITUCIÓN ─────────────────────────
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
    list_display  = ("codigo", "seccion")
    list_filter   = ("seccion__nivel__numero",)
    search_fields = ("codigo",)

@admin.register(Profesor)
class ProfesorAdmin(InstitucionScopedAdmin):
    list_display  = ("identificacion", "primer_apellido", "segundo_apellido", "nombres", "correo", "telefono")
    search_fields = ("identificacion", "primer_apellido", "segundo_apellido", "nombres")
    inlines       = [ClaseInline]

@admin.register(Clase)
class ClaseAdmin(InstitucionScopedAdmin):
    change_form_template = "admin/catalogos/clase/change_form.html"
    list_display        = ("materia", "subgrupo", "profesor", "periodo")
    list_filter         = ("periodo", "materia__tipo", "subgrupo__seccion__nivel__numero")
    autocomplete_fields = ("profesor", "materia", "subgrupo")

    # preserva campos marcados
    def response_add(self, request, obj, post_url_continue=None):
        if "_addanother" in request.POST:
            params = []
            for field in ("profesor", "materia", "subgrupo"):
                if request.POST.get(f"preserve_{field}") == "on":
                    params.append(f"{field}={getattr(obj, field).pk}")
            url = reverse("admin:catalogos_clase_add")
            if params:
                url += "?" + "&".join(params)
            return HttpResponseRedirect(url)
        return super().response_add(request, obj, post_url_continue)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        for field in ("profesor", "materia", "subgrupo"):
            if field in request.GET:
                initial[field] = request.GET[field]
        return initial
