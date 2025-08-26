# core/mixins.py
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
        
        # Para modelos que tienen campo 'institucion' directamente
        if hasattr(qs.model, 'institucion_id'):
            return qs.filter(institucion_id=request.institucion_activa_id)
        
        # Para modelos que obtienen institución a través de relaciones
        # (como MatriculaAcademica que la obtiene a través de estudiante)
        if hasattr(qs.model, 'estudiante') and hasattr(qs.model.estudiante.field, 'related_model'):
            return qs.filter(estudiante__institucion_id=request.institucion_activa_id)
        
        return qs

    def save_model(self, request, obj, form, change):
        # Si es creación y el modelo tiene campo 'institucion' directamente
        if not change and hasattr(obj, "institucion_id") and not obj.institucion_id:
            # Verificar que el campo realmente existe en el modelo
            if hasattr(obj._meta, 'get_field') and obj._meta.get_field('institucion_id', raise_exception=False):
                obj.institucion_id = request.institucion_activa_id
        super().save_model(request, obj, form, change)
