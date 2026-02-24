import logging

from django.contrib import admin
from django.db.models import Q

from .models import AsistenciaRegistro, AsistenciaSesion

logger = logging.getLogger(__name__)


class _AdminOnlyEditMixin:
    """
    Para usuarios no-superusuarios:
      - El modelo aparece en el sidebar si tienen access_libro_docente.
      - Ven solo sus sesiones/registros (filtradas por docente_asignacion o created_by).
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Diagnóstico: registros antes de filtros (solo en DEBUG)
        if logger.isEnabledFor(logging.DEBUG):
            total_antes = qs.count()
        # Usuario normal: solo sesiones donde es el docente asignado o el creador
        filtro_docente = Q(docente_asignacion__docente__usuario=request.user) | Q(created_by=request.user)
        qs = qs.filter(filtro_docente)
        if logger.isEnabledFor(logging.DEBUG):
            despues_docente = qs.count()
            logger.debug(
                "AsistenciaSesion get_queryset: total_antes=%s, despues_filtro_docente=%s, user=%s",
                total_antes, despues_docente, request.user.email,
            )
        # Restringir por institución activa si está definida
        inst_id = getattr(request, "institucion_activa_id", None)
        if inst_id:
            qs = qs.filter(institucion_id=inst_id)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "AsistenciaSesion get_queryset: despues_filtro_institucion=%s, inst_id=%s",
                    qs.count(), inst_id,
                )
        return qs


@admin.register(AsistenciaRegistro)
class AsistenciaRegistroAdmin(_AdminOnlyEditMixin, admin.ModelAdmin):
    list_display = ("sesion", "estudiante", "estado", "updated_at")
    list_filter = ("estado", "sesion__fecha", "sesion__institucion")
    search_fields = ("estudiante__primer_apellido", "estudiante__nombres", "estudiante__identificacion")
    readonly_fields = ("updated_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Usuario normal: solo registros de sesiones donde es el docente o creador
        filtro_sesion = (
            Q(sesion__docente_asignacion__docente__usuario=request.user) |
            Q(sesion__created_by=request.user)
        )
        qs = qs.filter(filtro_sesion)
        inst_id = getattr(request, "institucion_activa_id", None)
        if inst_id:
            qs = qs.filter(sesion__institucion_id=inst_id)
        return qs
