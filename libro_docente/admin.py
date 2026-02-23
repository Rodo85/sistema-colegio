from django.contrib import admin

from .models import AsistenciaRegistro, AsistenciaSesion


class AsistenciaRegistroInline(admin.TabularInline):
    model = AsistenciaRegistro
    extra = 0
    fields = ("estudiante", "estado", "observacion", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(AsistenciaSesion)
class AsistenciaSesionAdmin(admin.ModelAdmin):
    list_display = ("id", "docente_asignacion", "fecha", "sesion_numero", "periodo", "institucion", "curso_lectivo", "created_by", "created_at")
    list_filter = ("institucion", "curso_lectivo", "periodo", "fecha")
    search_fields = ("docente_asignacion__docente__usuario__last_name", "docente_asignacion__docente__usuario__first_name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [AsistenciaRegistroInline]
    date_hierarchy = "fecha"


@admin.register(AsistenciaRegistro)
class AsistenciaRegistroAdmin(admin.ModelAdmin):
    list_display = ("sesion", "estudiante", "estado", "updated_at")
    list_filter = ("estado", "sesion__fecha", "sesion__institucion")
    search_fields = ("estudiante__primer_apellido", "estudiante__nombres", "estudiante__identificacion")
    readonly_fields = ("updated_at",)
