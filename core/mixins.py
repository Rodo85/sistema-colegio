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
        
        # Para modelos que obtienen institución a través de estudiante
        # (como MatriculaAcademica que la obtiene a través de estudiante)
        # El estudiante usa una tabla intermedia EstudianteInstitucion
        if hasattr(qs.model, 'estudiante'):
            return qs.filter(
                estudiante__instituciones_estudiante__institucion_id=request.institucion_activa_id,
                estudiante__instituciones_estudiante__estado='activo'
            )
        
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Establece el valor inicial y filtra el queryset del campo institución
        para usuarios no superusuarios.
        """
        if db_field.name == "institucion" and not request.user.is_superuser:
            # Filtrar solo la institución activa del usuario
            from core.models import Institucion
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                kwargs["queryset"] = Institucion.objects.filter(id=institucion_id)
                # Establecer el valor inicial
                kwargs["initial"] = institucion_id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        """
        Personaliza el formulario para asegurar que el campo institución
        se establezca correctamente antes de la validación.
        """
        form = super().get_form(request, obj, **kwargs)
        
        # Si no es superusuario y el modelo tiene campo institución
        if not request.user.is_superuser and hasattr(form.Meta.model, 'institucion_id'):
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                # Verificar que el campo 'institucion' existe en el formulario
                if 'institucion' in form.base_fields:
                    form.base_fields['institucion'].initial = institucion_id
                # Si el campo no está en el formulario, agregarlo como campo oculto
                elif hasattr(form.Meta.model, 'institucion_id'):
                    from django import forms
                    from core.models import Institucion
                    # Crear un campo ForeignKey oculto
                    form.base_fields['institucion'] = forms.ModelChoiceField(
                        queryset=Institucion.objects.filter(id=institucion_id),
                        initial=institucion_id,
                        widget=forms.HiddenInput(),
                        required=True
                    )
                
        return form

    def save_model(self, request, obj, form, change):
        # Si es creación y el modelo tiene campo 'institucion' directamente
        if not change and hasattr(obj, "institucion_id") and not obj.institucion_id:
            # Verificar que el campo realmente existe en el modelo
            try:
                obj._meta.get_field('institucion_id')
                institucion_id = getattr(request, 'institucion_activa_id', None)
                if institucion_id:
                    obj.institucion_id = institucion_id
            except:
                # El campo no existe, no hacer nada
                pass
        super().save_model(request, obj, form, change)
