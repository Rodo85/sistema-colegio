from django.contrib import admin
from core.mixins import InstitucionScopedAdmin
from .models import RegistroIngreso


@admin.register(RegistroIngreso)
class RegistroIngresoAdmin(InstitucionScopedAdmin):
    list_display = ("institucion", "identificacion", "fecha_hora", "es_entrada", "observacion")
    search_fields = ("identificacion",)
    list_filter = ("institucion", "es_entrada", "fecha_hora")
    ordering = ("-fecha_hora",)
    readonly_fields = ("institucion",)
    
    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ()
        return ("institucion",)
















