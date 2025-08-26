from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Estudiante, MatriculaAcademica, PlantillaImpresionMatricula
from config_institucional.models import Nivel
from catalogos.models import CursoLectivo
from dal import autocomplete

class EspecialidadCursoLectivoWidget(autocomplete.ModelSelect2):
    """Widget personalizado para mostrar solo el nombre de la especialidad"""
    
    def label_from_instance(self, obj):
        """Muestra solo el nombre de la especialidad (ej: 'Ejecutivo comercial')"""
        if hasattr(obj, 'especialidad') and hasattr(obj.especialidad, 'nombre'):
            return obj.especialidad.nombre
        return str(obj)

class MatriculaAcademicaForm(forms.ModelForm):
    class Meta:
        model = MatriculaAcademica
        fields = '__all__'
        widgets = {
            # FLUJO DEPENDIENTE: Curso Lectivo → Especialidad, Sección, Subgrupo
            'especialidad': EspecialidadCursoLectivoWidget(
                url='especialidad-autocomplete', 
                forward=['curso_lectivo', 'nivel'],  # Especialidad depende de curso_lectivo y nivel
                attrs={
                    'data-placeholder': 'Seleccione primero un curso lectivo y un nivel...',
                    'data-allow-clear': True,
                }
            ),
            'seccion': autocomplete.ModelSelect2(
                url='seccion-autocomplete',
                forward=['curso_lectivo', 'nivel'],  # Sección depende de curso_lectivo y nivel
                attrs={
                    'data-placeholder': 'Seleccione primero un curso lectivo y un nivel...',
                    'data-allow-clear': True,
                }
            ),
            'subgrupo': autocomplete.ModelSelect2(
                url='subgrupo-autocomplete',
                forward=['curso_lectivo', 'seccion'],  # Subgrupo depende de curso_lectivo y seccion
                attrs={
                    'data-placeholder': 'Seleccione primero un curso lectivo y una sección...',
                    'data-allow-clear': True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # Dejar que el JavaScript maneje la visibilidad, como con provincia/cantón/distrito
        # El campo siempre está presente pero se oculta/muestra dinámicamente
        
        # Filtrar especialidades si tenemos datos iniciales
        if self.instance and self.instance.pk:
            self._filtrar_especialidades()
        elif self.initial:
            self._filtrar_especialidades()

    def _filtrar_especialidades(self):
        """Filtra las especialidades disponibles según la institución y curso lectivo"""
        try:
            if hasattr(self, 'instance') and self.instance and self.instance.pk:
                # Para edición
                if self.instance.estudiante and self.instance.curso_lectivo:
                    especialidades_disponibles = MatriculaAcademica.get_especialidades_disponibles(
                        institucion=self.instance.estudiante.institucion,
                        curso_lectivo=self.instance.curso_lectivo
                    )
                    self.fields['especialidad'].queryset = especialidades_disponibles
            elif self.initial:
                # Para creación con datos iniciales
                from config_institucional.models import CursoLectivo
                from core.models import Institucion
                
                curso_lectivo_id = self.initial.get('curso_lectivo')
                estudiante_id = self.initial.get('estudiante')
                
                if curso_lectivo_id and estudiante_id:
                    try:
                        curso_lectivo = CursoLectivo.objects.get(id=curso_lectivo_id)
                        estudiante = self.instance.estudiante if self.instance else None
                        if not estudiante and estudiante_id:
                            from .models import Estudiante
                            estudiante = Estudiante.objects.get(id=estudiante_id)
                        
                        if estudiante and curso_lectivo:
                            especialidades_disponibles = MatriculaAcademica.get_especialidades_disponibles(
                                institucion=estudiante.institucion,
                                curso_lectivo=curso_lectivo
                            )
                            self.fields['especialidad'].queryset = especialidades_disponibles
                    except (CursoLectivo.DoesNotExist, ValueError, Estudiante.DoesNotExist):
                        pass
                        
            # Si no se pudo filtrar, mostrar todas las especialidades disponibles
            if not hasattr(self, '_especialidades_filtradas') or not self._especialidades_filtradas:
                try:
                    from config_institucional.models import EspecialidadCursoLectivo
                    # Mostrar especialidades activas de la institución del usuario
                    if hasattr(self, 'request') and hasattr(self.request, 'institucion_activa_id'):
                        institucion_id = self.request.institucion_activa_id
                        if institucion_id:
                            especialidades = EspecialidadCursoLectivo.objects.filter(
                                institucion_id=institucion_id,
                                activa=True
                            ).select_related('especialidad')
                            self.fields['especialidad'].queryset = especialidades
                            self._especialidades_filtradas = True
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error al cargar especialidades de respaldo: {e}")
                    
        except Exception as e:
            # Log del error para debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error al filtrar especialidades: {e}")
            # Si hay algún error, no mostrar especialidades
            self.fields['especialidad'].queryset = self.fields['especialidad'].queryset.none()

    def clean(self):
        cleaned_data = super().clean()
        nivel = cleaned_data.get('nivel')
        especialidad = cleaned_data.get('especialidad')
        estudiante = cleaned_data.get('estudiante')
        curso_lectivo = cleaned_data.get('curso_lectivo')
        
        # Validar que la especialidad esté disponible para la institución y curso lectivo
        if especialidad and estudiante and curso_lectivo:
            try:
                especialidades_disponibles = MatriculaAcademica.get_especialidades_disponibles(
                    institucion=estudiante.institucion,
                    curso_lectivo=curso_lectivo
                )
                if especialidad not in especialidades_disponibles:
                    # Log para debugging
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Especialidad {especialidad} no disponible para estudiante {estudiante} "
                        f"en curso {curso_lectivo}. Disponibles: {list(especialidades_disponibles)}"
                    )
                    self.add_error('especialidad', 'Esta especialidad no está disponible para el curso lectivo seleccionado.')
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error al validar especialidad: {e}")
                self.add_error('especialidad', 'Error al validar la especialidad seleccionada.')
        
        # Décimo: especialidad obligatoria
        if nivel and hasattr(nivel, 'numero') and nivel.numero == 10:
            if not especialidad:
                self.add_error('especialidad', 'La especialidad es obligatoria para décimo.')
        # 11 y 12: si no hay especialidad previa, obligar a seleccionar
        elif nivel and hasattr(nivel, 'numero') and nivel.numero in [11, 12]:
            especialidad_10 = None
            if estudiante:
                # Buscar matrícula de décimo del mismo estudiante
                matricula_10 = MatriculaAcademica.objects.filter(
                    estudiante=estudiante, 
                    nivel__numero=10,
                    estado='activo'
                ).order_by('-id').first()
                if matricula_10:
                    especialidad_10 = matricula_10.especialidad
            
            # Solo requerir especialidad si no hay una previa de décimo
            if not especialidad and not especialidad_10:
                self.add_error('especialidad', 'Debe seleccionar la especialidad si no existe una asignada en décimo.')
        return cleaned_data

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'matricula/js/dependent-especialidad.js',  # Usar el archivo que funciona
            'matricula/js/clear-dependent-fields.js',  # Limpieza automática de campos dependientes
        )