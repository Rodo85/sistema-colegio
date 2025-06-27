# core/admin_utils.py
from django.contrib import admin

class InstitucionScopedAdmin(admin.ModelAdmin):
    """
    Mixin para que los ModelAdmin filtren y asignen automáticamente
    el campo 'institucion' según request.institucion_activa_id.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(institucion_id=request.institucion_activa_id)

    def save_model(self, request, obj, form, change):
        # Si es creación y el modelo tiene campo 'institucion'
        if not change and hasattr(obj, "institucion_id") and not obj.institucion_id:
            obj.institucion_id = request.institucion_activa_id
        super().save_model(request, obj, form, change)
