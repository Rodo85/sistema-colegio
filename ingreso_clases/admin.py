from django.contrib import admin
from .models import RegistroIngreso


@admin.register(RegistroIngreso)
class RegistroIngresoAdmin(admin.ModelAdmin):
    list_display = ("identificacion", "fecha_hora", "es_entrada", "observacion")
    search_fields = ("identificacion",)
    list_filter = ("es_entrada", "fecha_hora")
    ordering = ("-fecha_hora",)













