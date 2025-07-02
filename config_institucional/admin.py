from django.contrib import admin
from django.contrib.admin import RelatedOnlyFieldListFilter
from core.mixins import InstitucionScopedAdmin
from core.models import Institucion
from .models import Seccion, Subgrupo, Profesor, Clase
from catalogos.models import SubArea  

class SubgrupoInline(admin.TabularInline):
    model = Subgrupo
    extra = 0

class ClaseInline(admin.TabularInline):
    model = Clase
    extra = 0
    autocomplete_fields = ("subarea", "subgrupo")

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
    list_display = ("usuario", "institucion", "identificacion")
    search_fields = (
        "usuario__first_name",
        "usuario__last_name",
        "usuario__second_last_name",
        "usuario__email",
        "identificacion",
    )
    autocomplete_fields = ("usuario",)

    # ---------- Permitir al superuser editar 'institucion' ----------
    def get_readonly_fields(self, request, obj=None):
        # Superuser: ningún campo de solo lectura
        if request.user.is_superuser:
            return ()
        # Director: 'institucion' se rellena automáticamente y no se puede cambiar
        return ("institucion",)

    # ---------- Filtrado del combo de institución ----------
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "institucion" and not request.user.is_superuser:
            # Para directores muestra solo su institución
            kwargs["queryset"] = Institucion.objects.filter(
                id=request.institucion_activa_id
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Clase)
class ClaseAdmin(InstitucionScopedAdmin):
    list_display = ("subarea", "subgrupo", "profesor", "periodo")
    list_filter  = (
        "periodo",
        "subarea__especialidad__modalidad__nombre",
        ("subgrupo", RelatedOnlyFieldListFilter),
    )
    autocomplete_fields = ("profesor", "subarea", "subgrupo")

    # ---------- Filtrar combos y ajustar etiqueta de Subárea ----------
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ❶ Filtrado por institución (solo para directores)
        if not request.user.is_superuser:
            if db_field.name == "profesor":
                kwargs["queryset"] = Profesor.objects.filter(
                    institucion_id=request.institucion_activa_id
                )
            elif db_field.name == "subgrupo":
                kwargs["queryset"] = Subgrupo.objects.filter(
                    seccion__nivel__institucion_id=request.institucion_activa_id
                )
            elif db_field.name == "subarea":
                kwargs["queryset"] = SubArea.objects.filter(
                    subareainstitucion__institucion_id=request.institucion_activa_id
                ).distinct()
            elif db_field.name == "institucion":
                kwargs["queryset"] = Institucion.objects.filter(
                    id=request.institucion_activa_id
                )

        # ❷ Obtener el form-field original
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)

        # ❸ Personalizar SOLO la etiqueta del campo Subárea
        if db_field.name == "subarea":
            formfield.label_from_instance = lambda obj: obj.nombre

        return formfield

    def get_readonly_fields(self, request, obj=None):
        return () if request.user.is_superuser else ("institucion",)



