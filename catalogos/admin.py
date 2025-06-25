from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import (
    TipoIdentificacion,
    Nacionalidad,
    Adecuacion,
    Especialidad,
    Nivel,
    Seccion,
    Subgrupo,
    Materia,
    Profesor,
    Clase,
)
from .forms import EspecialidadForm


# ──────────────────────────
# 1. Catálogos “simples”
# ──────────────────────────
admin.site.register([
    TipoIdentificacion,
    Nacionalidad,
    Adecuacion,
])

# ──────────────────────────
# 2. Especialidad con formulario de años
# ──────────────────────────
@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    form = EspecialidadForm
    list_display  = ("nombre", "año")
    list_filter   = ("año",)
    search_fields = ("nombre",)


# ──────────────────────────
# 3. Inlines
# ──────────────────────────
class SubgrupoInline(admin.TabularInline):
    model = Subgrupo
    extra = 0


class ClaseInline(admin.TabularInline):
    model = Clase
    extra = 0
    autocomplete_fields = ("materia", "subgrupo")


# ──────────────────────────
# 4. ModelAdmin de catálogos con jerarquía
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
    list_display    = ("codigo", "seccion")
    list_filter     = ("seccion__nivel__numero",)
    search_fields   = ("seccion__nivel__numero", "seccion__numero", "letra")


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display  = ("nombre", "tipo")
    list_filter   = ("tipo",)
    search_fields = ("nombre",)


@admin.register(Profesor)
class ProfesorAdmin(admin.ModelAdmin):
    list_display  = (
        "identificacion",
        "primer_apellido",
        "segundo_apellido",
        "nombres",
        "correo",
        "telefono",
    )
    search_fields = (
        "identificacion",
        "primer_apellido",
        "segundo_apellido",
        "nombres",
    )
    inlines = [ClaseInline]


# ──────────────────────────
# 5. ClaseAdmin con “preservar campos”
# ──────────────────────────
@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    change_form_template = "admin/catalogos/clase/change_form.html"
    list_display         = ("materia", "subgrupo", "profesor", "periodo")
    list_filter          = (
        "periodo",
        "materia__tipo",
        "subgrupo__seccion__nivel__numero",
        "profesor"
    )
    autocomplete_fields  = ("profesor", "materia", "subgrupo")

    def response_add(self, request, obj, post_url_continue=None):
        # Si pulsó “Guardar y añadir otro”, trasladamos los campos marcados
        if "_addanother" in request.POST:
            params = []
            for field in ("profesor", "materia", "subgrupo"):
                if request.POST.get(f"preserve_{field}") == "on":
                    val = getattr(obj, field)
                    params.append(f"{field}={val.pk}")
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
