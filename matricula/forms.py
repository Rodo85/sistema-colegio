from django import forms
from .models import MatriculaAcademica, Nivel
from django.utils.safestring import mark_safe

class MatriculaAcademicaForm(forms.ModelForm):
    class Meta:
        model = MatriculaAcademica
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Obtener el nivel (puede ser instancia o id)
        nivel = self.initial.get('nivel') or self.data.get('nivel') or getattr(self.instance, 'nivel', None)
        estudiante = self.initial.get('estudiante') or self.data.get('estudiante') or getattr(self.instance, 'estudiante', None)
        # Si el nivel es décimo (10)
        if nivel and hasattr(nivel, 'nombre') and (str(nivel.nombre).strip() == '10' or str(nivel) == '10'):
            self.fields['especialidad'].required = True
            self.fields['especialidad'].widget.attrs.pop('readonly', None)
        # Si el nivel es 11 o 12
        elif nivel and hasattr(nivel, 'nombre') and (str(nivel.nombre).strip() in ['11', '12'] or str(nivel) in ['11', '12']):
            # Buscar la especialidad de décimo
            especialidad_10 = None
            if estudiante:
                matricula_10 = MatriculaAcademica.objects.filter(estudiante=estudiante, nivel__nombre='10').order_by('-id').first()
                if matricula_10:
                    especialidad_10 = matricula_10.especialidad
            if especialidad_10:
                self.fields['especialidad'].initial = especialidad_10
            self.fields['especialidad'].required = False
            self.fields['especialidad'].widget.attrs.pop('readonly', None)
        else:
            # Otros niveles: especialidad no requerida
            self.fields['especialidad'].required = False
            self.fields['especialidad'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        nivel = cleaned_data.get('nivel')
        especialidad = cleaned_data.get('especialidad')
        estudiante = cleaned_data.get('estudiante')
        # Décimo: especialidad obligatoria
        if nivel and hasattr(nivel, 'nombre') and (str(nivel.nombre).strip() == '10' or str(nivel) == '10'):
            if not especialidad:
                self.add_error('especialidad', 'La especialidad es obligatoria para décimo.')
        # 11 y 12: si no hay especialidad previa, obligar a seleccionar
        elif nivel and hasattr(nivel, 'nombre') and (str(nivel.nombre).strip() in ['11', '12'] or str(nivel) in ['11', '12']):
            especialidad_10 = None
            if estudiante:
                matricula_10 = MatriculaAcademica.objects.filter(estudiante=estudiante, nivel__nombre='10').order_by('-id').first()
                if matricula_10:
                    especialidad_10 = matricula_10.especialidad
            if not especialidad and not especialidad_10:
                self.add_error('especialidad', 'Debe seleccionar la especialidad si no existe una asignada en décimo.')
        return cleaned_data