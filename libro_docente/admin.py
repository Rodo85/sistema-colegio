import logging

from django.contrib import admin
from django.db.models import Q

from core.mixins import HideInstitucionFilterMixin
from .models import ActividadEvaluacion, AsistenciaRegistro, AsistenciaSesion, IndicadorActividad, PuntajeIndicador

logger = logging.getLogger(__name__)


class _AdminOnlyEditMixin:
    """
    Para usuarios no-superusuarios:
      - El modelo aparece en el sidebar si tienen access_libro_docente.
      - Ven solo sus sesiones/registros (filtradas por docente_asignacion o created_by).
      - Pueden eliminar sus propias sesiones (has_delete_permission).
      - No pueden agregar ni editar registros.
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
        if request.user.is_superuser:
            return True
        if not self._puede_ver_modulo(request):
            return False
        if obj is None:
            return True  # Lista: get_queryset ya filtra
        # Objeto concreto: verificar que pertenece al usuario
        from .models import AsistenciaSesion
        if isinstance(obj, AsistenciaSesion):
            es_docente = obj.docente_asignacion.docente.usuario_id == request.user.pk
            es_creador = obj.created_by_id == request.user.pk
            return es_docente or es_creador
        if hasattr(obj, "sesion"):
            sesion = obj.sesion
            es_docente = sesion.docente_asignacion.docente.usuario_id == request.user.pk
            es_creador = sesion.created_by_id == request.user.pk
            return es_docente or es_creador
        return False


class AsistenciaRegistroInline(admin.TabularInline):
    model = AsistenciaRegistro
    extra = 0
    fields = ("estudiante", "estado", "lecciones_injustificadas", "observacion", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(AsistenciaSesion)
class AsistenciaSesionAdmin(HideInstitucionFilterMixin, _AdminOnlyEditMixin, admin.ModelAdmin):
    list_display = ("id", "docente_asignacion", "fecha", "lecciones", "sesion_numero", "periodo", "institucion", "curso_lectivo", "created_by", "created_at")
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
class AsistenciaRegistroAdmin(HideInstitucionFilterMixin, _AdminOnlyEditMixin, admin.ModelAdmin):
    list_display = ("sesion", "estudiante", "estado", "lecciones_injustificadas", "updated_at")
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


# ═══════════════════════════════════════════════════════════════════════════
#  EVALUACIÓN POR INDICADORES (TAREAS / COTIDIANOS)
# ═══════════════════════════════════════════════════════════════════════════


class IndicadorActividadInline(admin.TabularInline):
    model = IndicadorActividad
    extra = 1
    fields = ("orden", "descripcion", "escala_min", "escala_max", "activo")
    ordering = ("orden", "id")


class PuntajeIndicadorInline(admin.TabularInline):
    model = PuntajeIndicador
    extra = 0
    fields = ("estudiante", "puntaje_obtenido", "observacion", "updated_at")
    readonly_fields = ("updated_at",)
    autocomplete_fields = ("estudiante",)


class _AdminEvaluacionSoloSuperuserMixin:
    """Oculta ActividadEvaluacion, IndicadorActividad, PuntajeIndicador del sidebar para docentes.
    Solo superadmin los ve; docentes usan el flujo Mis Asignaciones."""
    def has_module_permission(self, request):
        return request.user.is_superuser


@admin.register(ActividadEvaluacion)
class ActividadEvaluacionAdmin(_AdminEvaluacionSoloSuperuserMixin, HideInstitucionFilterMixin, admin.ModelAdmin):
    list_display = (
        "titulo",
        "tipo_componente",
        "estado",
        "docente_asignacion",
        "periodo",
        "institucion",
        "created_at",
    )
    list_filter = ("tipo_componente", "estado", "institucion", "periodo")
    search_fields = ("titulo", "descripcion")
    readonly_fields = ("created_at", "updated_at")
    inlines = [IndicadorActividadInline]
    date_hierarchy = "fecha_asignacion"
    autocomplete_fields = ("docente_asignacion",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Docente: solo sus asignaciones
        qs = qs.filter(docente_asignacion__docente__usuario=request.user)
        inst_id = getattr(request, "institucion_activa_id", None)
        if inst_id:
            qs = qs.filter(institucion_id=inst_id)
        return qs

    def save_model(self, request, obj, form, change):
        if not change and obj.docente_asignacion_id:
            da = obj.docente_asignacion
            if not obj.institucion_id:
                obj.institucion_id = da.subarea_curso.institucion_id
            if not obj.curso_lectivo_id:
                obj.curso_lectivo_id = da.curso_lectivo_id
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(IndicadorActividad)
class IndicadorActividadAdmin(_AdminEvaluacionSoloSuperuserMixin, admin.ModelAdmin):
    list_display = ("actividad", "orden", "descripcion", "escala_min", "escala_max", "activo", "created_at")
    list_filter = ("activo", "actividad__tipo_componente")
    search_fields = ("descripcion",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [PuntajeIndicadorInline]
    autocomplete_fields = ("actividad",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        qs = qs.filter(actividad__docente_asignacion__docente__usuario=request.user)
        inst_id = getattr(request, "institucion_activa_id", None)
        if inst_id:
            qs = qs.filter(actividad__institucion_id=inst_id)
        return qs


@admin.register(PuntajeIndicador)
class PuntajeIndicadorAdmin(_AdminEvaluacionSoloSuperuserMixin, admin.ModelAdmin):
    list_display = ("indicador", "estudiante", "puntaje_obtenido", "observacion", "updated_at")
    list_filter = ("indicador__actividad__tipo_componente",)
    search_fields = ("estudiante__primer_apellido", "estudiante__nombres", "estudiante__identificacion")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("indicador", "estudiante")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        qs = qs.filter(indicador__actividad__docente_asignacion__docente__usuario=request.user)
        inst_id = getattr(request, "institucion_activa_id", None)
        if inst_id:
            qs = qs.filter(indicador__actividad__institucion_id=inst_id)
        return qs
