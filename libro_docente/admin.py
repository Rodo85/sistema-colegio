from django.contrib import admin

from .models import AsistenciaRegistro, AsistenciaSesion


class _AdminOnlyEditMixin:
    """
    Para usuarios no-superusuarios:
      - El modelo aparece en el sidebar si tienen access_libro_docente.
      - Al entrar a la lista ven una tabla vacía (get_queryset devuelve .none()).
      - No pueden agregar, editar ni eliminar registros.
    Superusuarios tienen acceso completo.
    """
    def _puede_ver_modulo(self, request):
        return request.user.is_superuser or request.user.has_perm("libro_docente.access_libro_docente")

    def has_module_permission(self, request):
        return self._puede_ver_modulo(request)

    def has_view_permission(self, request, obj=None):
        return self._puede_ver_modulo(request)

    def get_model_perms(self, request):
        if request.user.is_superuser:
            return super().get_model_perms(request)
        if self._puede_ver_modulo(request):
            return {"view": True}
        return {}

    def get_queryset(self, request):
        if not request.user.is_superuser:
            return super().get_queryset(request).none()
        return super().get_queryset(request)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class AsistenciaRegistroInline(admin.TabularInline):
    model = AsistenciaRegistro
    extra = 0
    fields = ("estudiante", "estado", "observacion", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(AsistenciaSesion)
class AsistenciaSesionAdmin(_AdminOnlyEditMixin, admin.ModelAdmin):
    list_display = ("id", "docente_asignacion", "fecha", "sesion_numero", "periodo", "institucion", "curso_lectivo", "created_by", "created_at")
    list_filter = ("institucion", "curso_lectivo", "periodo", "fecha")
    search_fields = ("docente_asignacion__docente__usuario__last_name", "docente_asignacion__docente__usuario__first_name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [AsistenciaRegistroInline]
    date_hierarchy = "fecha"


@admin.register(AsistenciaRegistro)
class AsistenciaRegistroAdmin(_AdminOnlyEditMixin, admin.ModelAdmin):
    list_display = ("sesion", "estudiante", "estado", "updated_at")
    list_filter = ("estado", "sesion__fecha", "sesion__institucion")
    search_fields = ("estudiante__primer_apellido", "estudiante__nombres", "estudiante__identificacion")
    readonly_fields = ("updated_at",)
