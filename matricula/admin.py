from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from core.mixins import InstitucionScopedAdmin
from .models import Estudiante, EncargadoEstudiante, PersonaContacto, MatriculaAcademica, PlantillaImpresionMatricula

from catalogos.models import Provincia, Canton, Distrito
from .forms import MatriculaAcademicaForm
from .widgets import ImagePreviewWidget
from core.models import Institucion

# ─────────────────────────────  Filtros Personalizados  ────────────────────────────
class InstitucionScopedFilter(admin.SimpleListFilter):
    """Filtro base que se filtra por institución activa del usuario"""
    
    def queryset(self, request, queryset):
        if request.user.is_superuser:
            return queryset
        institucion_id = getattr(request, 'institucion_activa_id', None)
        if institucion_id:
            return queryset.filter(institucion_id=institucion_id)
        return queryset.none()

class NivelInstitucionFilter(InstitucionScopedFilter):
    title = 'Nivel'
    parameter_name = 'nivel_institucion'
    
    def lookups(self, request, model_admin):
        from config_institucional.models import NivelInstitucion
        if request.user.is_superuser:
            niveles = NivelInstitucion.objects.values_list('nivel__id', 'nivel__numero', 'nivel__nombre').distinct()
            # Formatear como "7 (Séptimo)", "8 (Octavo)", etc.
            return [(nivel[0], f"{nivel[1]} ({nivel[2]})") for nivel in niveles]
        else:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                niveles = NivelInstitucion.objects.filter(
                    institucion_id=institucion_id
                ).values_list('nivel__id', 'nivel__numero', 'nivel__nombre').distinct()
                # Formatear como "7 (Séptimo)", "8 (Octavo)", etc.
                return [(nivel[0], f"{nivel[1]} ({nivel[2]})") for nivel in niveles]
            else:
                return []

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(nivel_id=self.value())
        return queryset

class SeccionInstitucionFilter(InstitucionScopedFilter):
    title = 'Sección'
    parameter_name = 'seccion_institucion'
    
    def lookups(self, request, model_admin):
        from config_institucional.models import SeccionCursoLectivo
        from catalogos.models import CursoLectivo
        import datetime
        
        # Obtener el curso lectivo seleccionado o el año actual por defecto
        curso_lectivo_id = request.GET.get('curso_lectivo')
        if not curso_lectivo_id:
            curso_actual = CursoLectivo.objects.filter(anio=datetime.date.today().year).first()
            curso_lectivo_id = curso_actual.id if curso_actual else None
        
        if not curso_lectivo_id:
            return []
        
        if request.user.is_superuser:
            secciones = SeccionCursoLectivo.objects.filter(
                curso_lectivo_id=curso_lectivo_id
            ).values_list('seccion__id', 'seccion__nivel__numero', 'seccion__numero').distinct()
        else:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                secciones = SeccionCursoLectivo.objects.filter(
                    institucion_id=institucion_id,
                    curso_lectivo_id=curso_lectivo_id
                ).values_list('seccion__id', 'seccion__nivel__numero', 'seccion__numero').distinct()
            else:
                return []
        
        # Formatear como "7-1", "7-2", etc.
        return [(seccion[0], f"{seccion[1]}-{seccion[2]}") for seccion in secciones]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(seccion_id=self.value())
        return queryset

class InstitucionMatriculaFilter(admin.SimpleListFilter):
    """Filtro de institución para matrículas (solo superusuarios)"""
    title = 'Institución'
    parameter_name = 'institucion_matricula'
    
    def lookups(self, request, model_admin):
        if not request.user.is_superuser:
            return []
        
        from core.models import Institucion
        from django.utils import timezone
        # Filtrar instituciones activas usando fecha_fin >= hoy
        instituciones = Institucion.objects.filter(
            fecha_fin__gte=timezone.now().date()
        ).order_by('nombre')
        return [(inst.id, inst.nombre) for inst in instituciones]
    
    def queryset(self, request, queryset):
        if not request.user.is_superuser:
            return queryset
        
        if self.value():
            return queryset.filter(estudiante__institucion_id=self.value())
        return queryset

class SubgrupoInstitucionFilter(InstitucionScopedFilter):
    title = 'Subgrupo'
    parameter_name = 'subgrupo_institucion'
    
    def lookups(self, request, model_admin):
        from config_institucional.models import SubgrupoCursoLectivo
        from catalogos.models import CursoLectivo
        import datetime
        
        # Obtener el curso lectivo seleccionado o el año actual por defecto
        curso_lectivo_id = request.GET.get('curso_lectivo')
        if not curso_lectivo_id:
            curso_actual = CursoLectivo.objects.filter(anio=datetime.date.today().year).first()
            curso_lectivo_id = curso_actual.id if curso_actual else None
        
        if not curso_lectivo_id:
            return []
        
        if request.user.is_superuser:
            subgrupos = SubgrupoCursoLectivo.objects.filter(
                curso_lectivo_id=curso_lectivo_id
            ).values_list(
                'subgrupo__id', 
                'subgrupo__seccion__nivel__numero', 
                'subgrupo__seccion__numero', 
                'subgrupo__letra'
            ).distinct()
        else:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                subgrupos = SubgrupoCursoLectivo.objects.filter(
                    institucion_id=institucion_id,
                    curso_lectivo_id=curso_lectivo_id
                ).values_list(
                    'subgrupo__id', 
                    'subgrupo__seccion__nivel__numero', 
                    'subgrupo__seccion__numero', 
                    'subgrupo__letra'
                ).distinct()
            else:
                return []
        
        # Formatear como "7-1A", "7-1B", etc.
        return [(subgrupo[0], f"{subgrupo[1]}-{subgrupo[2]}{subgrupo[3]}") for subgrupo in subgrupos]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(subgrupo_id=self.value())
        return queryset

class EspecialidadInstitucionFilter(InstitucionScopedFilter):
    title = 'Especialidad'
    parameter_name = 'especialidad_institucion'
    
    def lookups(self, request, model_admin):
        from config_institucional.models import EspecialidadCursoLectivo
        from catalogos.models import CursoLectivo
        import datetime
        
        # Obtener el curso lectivo seleccionado o el año actual por defecto
        curso_lectivo_id = request.GET.get('curso_lectivo')
        if not curso_lectivo_id:
            curso_actual = CursoLectivo.objects.filter(anio=datetime.date.today().year).first()
            curso_lectivo_id = curso_actual.id if curso_actual else None
        
        if not curso_lectivo_id:
            return []
        
        if request.user.is_superuser:
            especialidades = EspecialidadCursoLectivo.objects.filter(
                curso_lectivo_id=curso_lectivo_id
            ).values_list('especialidad__id', 'especialidad__nombre').distinct()
        else:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                especialidades = EspecialidadCursoLectivo.objects.filter(
                    institucion_id=institucion_id,
                    curso_lectivo_id=curso_lectivo_id
                ).values_list('especialidad__id', 'especialidad__nombre').distinct()
            else:
                especialidades = []
        return especialidades

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(especialidad_id=self.value())
        return queryset

class CursoLectivoFilter(admin.SimpleListFilter):
    title = 'Curso Lectivo'
    parameter_name = 'curso_lectivo'
    
    def lookups(self, request, model_admin):
        from catalogos.models import CursoLectivo
        import datetime
        
        # Obtener todos los cursos lectivos ordenados por año (más reciente primero)
        cursos = CursoLectivo.objects.values_list('id', 'anio', 'nombre').order_by('-anio')
        return [(curso[0], f"{curso[1]} - {curso[2]}") for curso in cursos]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(curso_lectivo_id=self.value())
        else:
            # Si no hay filtro seleccionado, filtrar por el año actual por defecto
            from catalogos.models import CursoLectivo
            import datetime
            curso_actual = CursoLectivo.objects.filter(anio=datetime.date.today().year).first()
            if curso_actual:
                return queryset.filter(curso_lectivo_id=curso_actual.id)
        return queryset
    
    def choices(self, changelist):
        """Personalizar choices para tener seleccionado por defecto el año actual"""
        from catalogos.models import CursoLectivo
        import datetime
        
        # Obtener el curso lectivo del año actual
        curso_actual = CursoLectivo.objects.filter(anio=datetime.date.today().year).first()
        
        # Si no hay un valor seleccionado y existe un curso para el año actual, seleccionarlo
        if not self.value() and curso_actual:
            # Modificar temporalmente el valor para que aparezca seleccionado
            self.used_parameters[self.parameter_name] = str(curso_actual.id)
        
        return super().choices(changelist)

# ─────────────────────────────  Formularios  ────────────────────────────
class EstudianteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'provincia' in self.fields and not self.instance.pk:
            primera_provincia = Provincia.objects.first()
            if primera_provincia:
                self.fields['provincia'].initial = primera_provincia.id
        # Permitir que el modelo autogenere el correo si no se ingresa
        if 'correo' in self.fields:
            self.fields['correo'].required = False

    def clean(self):
        cleaned_data = super().clean()
        tipo_identificacion = cleaned_data.get('tipo_identificacion')
        identificacion = cleaned_data.get('identificacion')
        foto = cleaned_data.get('foto')
        
        # Validar identificación para Cédula de identidad
        if tipo_identificacion and identificacion:
            # Verificar si es "Cédula de identidad" (asumiendo que el nombre contiene "Cédula")
            if 'cédula' in str(tipo_identificacion).lower() or 'cedula' in str(tipo_identificacion).lower():
                # Limpiar la identificación de guiones y espacios
                identificacion_limpia = identificacion.replace('-', '').replace(' ', '')
                
                # Validar que tenga exactamente 9 caracteres
                if len(identificacion_limpia) != 9:
                    self.add_error('identificacion', 
                        'La cédula de identidad debe tener exactamente 9 dígitos. '
                        f'Si es cédula de identidad no ingrese guiones. (tiene {len(identificacion_limpia)} caracteres)')
                
                # Validar que solo contenga números
                if not identificacion_limpia.isdigit():
                    self.add_error('identificacion', 
                        'La cédula de identidad solo debe contener números. '
                        'Si es cédula de identidad no ingrese guiones.')
                
                # Si pasa la validación, guardar la versión limpia
                if len(self.errors) == 0:
                    cleaned_data['identificacion'] = identificacion_limpia
        
        # Validar foto si se proporciona
        if foto and hasattr(foto, 'size'):
            # Verificar tamaño del archivo (máximo 5MB)
            if foto.size > 5 * 1024 * 1024:  # 5MB en bytes
                self.add_error('foto', 'La imagen no puede ser mayor a 5MB.')
            
            # Verificar tipo de archivo
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if hasattr(foto, 'content_type') and foto.content_type not in allowed_types:
                self.add_error('foto', 'Solo se permiten archivos de imagen (JPG, PNG, GIF).')
        
        return cleaned_data

    class Meta:
        model = Estudiante
        # Excluir institucion para que no dependa del POST
        exclude = ('institucion',)
        widgets = {
            'provincia': forms.Select(attrs={'id': 'id_provincia'}),
            'canton': forms.Select(attrs={'id': 'id_canton'}),
            'distrito': forms.Select(attrs={'id': 'id_distrito'}),
            'identificacion': forms.TextInput(attrs={
                'autocomplete': 'off',
                'placeholder': "Si es cédula de identidad no ingrese guiones. Ejemplo: 914750521",
                'title': 'Ingrese 9 dígitos sin guiones ni espacios'
            }),
            'foto': ImagePreviewWidget(),
            'numero_poliza': forms.TextInput(attrs={'autocomplete': 'off', 'name': 'num_poliza_custom', 'id': 'id_num_poliza_custom'}),
            'fecha_matricula': forms.TextInput(attrs={'autocomplete': 'off', 'name': 'fecha_matricula_custom', 'id': 'id_fecha_matricula_custom'}),
        }

    class Media:
        js = (
            'admin/js/jquery.init.js',
            "matricula/js/dependent-dropdowns.js",
            "matricula/js/autocomplete-correo.js",
        )

class PersonaContactoForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        tipo_identificacion = cleaned_data.get('tipo_identificacion')
        identificacion = cleaned_data.get('identificacion')
        
        # Validar identificación para Cédula de identidad
        if tipo_identificacion and identificacion:
            tipo_nombre = str(tipo_identificacion).lower()
            if 'cédula' in tipo_nombre or 'cedula' in tipo_nombre:
                # Limpiar la identificación de guiones y espacios
                identificacion_limpia = identificacion.replace('-', '').replace(' ', '')
                
                # Validar que tenga exactamente 9 caracteres
                if len(identificacion_limpia) != 9:
                    self.add_error('identificacion', 
                        'La cédula de identidad debe tener exactamente 9 dígitos. '
                        f'Si es cédula de identidad no ingrese guiones. (tiene {len(identificacion_limpia)} caracteres)')
                
                # Validar que solo contenga números
                if not identificacion_limpia.isdigit():
                    self.add_error('identificacion', 
                        'La cédula de identidad solo debe contener números. '
                        'Si es cédula de identidad no ingrese guiones.')
                
                # Si pasa la validación, guardar la versión limpia
                if len(self.errors) == 0:
                    cleaned_data['identificacion'] = identificacion_limpia
        
        return cleaned_data

    class Meta:
        model  = PersonaContacto
        fields = "__all__"
        widgets = {
            "identificacion": forms.TextInput(attrs={
                "autocomplete": "off",
                "placeholder": "Ingrese la identificación según el tipo seleccionado",
                "title": "Para cédula: 9 dígitos sin guiones. Para DIMEX: formato correspondiente"
            }),
        }
    class Media:
        js = (
            'admin/js/jquery.init.js',
        )

# ────────────────────────────  Inline  ──────────────────────────────────
class EncargadoInline(admin.TabularInline):
    model = EncargadoEstudiante
    extra = 0
    fields = ("persona_contacto", "parentesco", "convivencia", "principal")
    readonly_fields = ()

class MatriculaAcademicaInline(admin.StackedInline):  # Cambiado a StackedInline para vista vertical
    model = MatriculaAcademica
    form = MatriculaAcademicaForm
    extra = 0
    fields = ('curso_lectivo', 'nivel', 'seccion', 'subgrupo', 'estado', 'especialidad')
    # Permitir histórico, no forzar matrícula inmediata
    # Validación de matrícula activa se moverá al modelo
    
    class Media:
        js = (
            'admin/js/jquery.init.js',
            'matricula/js/dependent-especialidad.js',  # Para inlines también
            'matricula/js/clear-dependent-fields.js',  # Limpieza automática de campos dependientes
        )

# ────────────────────────  Estudiante admin  ───────────────────────────
@admin.register(Estudiante)
class EstudianteAdmin(InstitucionScopedAdmin):
    form    = EstudianteForm
    inlines = [EncargadoInline]
    fields = None  # Fuerza el uso de fieldsets

    def get_fieldsets(self, request, obj=None):
        fieldsets = []
        # Solo superadmin ve Información Institucional
        if request.user.is_superuser:
            fieldsets.append(
                ('Información Institucional', {
                    'fields': ('institucion',),
                    'classes': ('collapse',)
                })
            )
        # Usuarios normales: no incluir campo institucion en el formulario
        fieldsets.append(
            ('Datos Personales', {
                'fields': (
                    'tipo_estudiante',
                    'tipo_identificacion', 'identificacion',
                    'primer_apellido', 'segundo_apellido', 'nombres',
                    'fecha_nacimiento', 'sexo', 'nacionalidad',
                    'celular', 'telefono_casa', 'correo',
                    'foto',
                ),
                'description': 'Información personal del estudiante.'
            })
        )
        

        # Domicilio (antes Dirección)
        fieldsets.append(
            ('Domicilio', {
                'fields': ('provincia', 'canton', 'distrito', 'direccion_exacta'),
                'description': 'Seleccione la provincia para cargar los cantones disponibles, luego seleccione el cantón para cargar los distritos.'
            })
        )
        # Datos Académicos y de Salud
        fieldsets.append(
            ('Datos Académicos y de Salud', {
                'fields': (
                    'ed_religiosa', 'adecuacion',
                    'numero_poliza', 'rige_poliza', 'vence_poliza',
                    'presenta_enfermedad', 'detalle_enfermedad', 'medicamento_consume',
                    'autoriza_derecho_imagen',
                ),
            })
        )
        return fieldsets

    def get_list_display(self, request):
        """Agregar enlaces de acción personalizados"""
        # Guardar el request para usarlo en acciones
        self._request = request
        base_display = ("identificacion", "primer_apellido", "segundo_apellido", "nombres", "tipo_estudiante", "acciones")
        return base_display

    def acciones(self, obj):
        """Enlaces de acción para cada estudiante"""
        if obj.pk:
            # Obtener la URL del admin de matrícula
            from django.urls import reverse
            try:
                url = reverse('admin:matricula_matriculaacademica_add')
                url += f'?estudiante={obj.pk}'
                # Si tenemos el request guardado y no es superusuario, agregar la institución
                if hasattr(self, '_request') and not self._request.user.is_superuser:
                    institucion_id = getattr(self._request, 'institucion_activa_id', None)
                    if institucion_id:
                        url += f'&_institucion={institucion_id}'
                return format_html(
                    '<a class="button" href="{}" style="padding: 3px 8px; background: #417690; color: white; text-decoration: none; border-radius: 4px;">📚 Matrícula</a>',
                    url
                )
            except Exception as e:
                # Si hay error, mostrar enlace simple
                return format_html(
                    '<a class="button" href="/admin/matricula/matriculaacademica/add/?estudiante={}" style="padding: 3px 8px; background: #417690; color: white; text-decoration: none; border-radius: 4px;">📚 Matrícula</a>',
                    obj.pk
                )
        return ""
    acciones.short_description = "Acciones"
    acciones.allow_tags = True



    def foto_preview(self, obj):
        """Vista previa de la foto del estudiante"""
        if obj.foto:
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px; border-radius: 5px; border: 2px solid #ddd;" title="{}" />',
                obj.foto.url, obj.foto.name
            )
        return format_html(
            '<span style="color: #999; font-style: italic;">Sin foto</span>'
        )
    foto_preview.short_description = "Foto"
    
    def get_readonly_fields(self, request, obj=None):
        # No exponer 'institucion' a usuarios normales
        if request.user.is_superuser:
            return ()
        return ()
    
    def get_form(self, request, obj=None, **kwargs):
        """Personalizar el formulario según el usuario y forzar institución."""
        Form = super().get_form(request, obj, **kwargs)
        institucion_id = getattr(request, 'institucion_activa_id', None)
        is_super = request.user.is_superuser

        class FormWithInst(Form):
            def __init__(self, *args, **kw):
                super().__init__(*args, **kw)
                # Etiqueta
                if self.base_fields.get('sexo'):
                    self.base_fields['sexo'].label = "Género"

                if is_super or not institucion_id:
                    return

                # Campo oculto (aunque no esté en fieldsets)
                from core.models import Institucion
                if 'institucion' not in self.fields:
                    self.fields['institucion'] = forms.ModelChoiceField(
                        queryset=Institucion.objects.filter(id=institucion_id),
                        initial=institucion_id,
                        widget=forms.HiddenInput(),
                        required=True,
                    )
                else:
                    self.fields['institucion'].widget = forms.HiddenInput()
                    self.fields['institucion'].required = True
                    self.fields['institucion'].initial = institucion_id

                # Inyectar en POST si falta
                if self.is_bound:
                    data = self.data.copy()
                    key = self.add_prefix('institucion')
                    if not data.get(key):
                        data[key] = str(institucion_id)
                        self.data = data

                # Fijar en la instancia antes de validaciones del modelo
                self.instance.institucion_id = institucion_id

            def clean(self):
                if not is_super and institucion_id:
                    self.instance.institucion_id = institucion_id
                return super().clean()

        return FormWithInst

    # Búsqueda por identificación y nombre
    search_fields = ("identificacion", "primer_apellido", "segundo_apellido", "nombres")
    # Filtros incluyendo foto
    list_filter = ('tipo_estudiante', 'sexo', 'nacionalidad')
    list_per_page = 25
    ordering = ("primer_apellido", "nombres")

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        # Solo limitar resultados si no es una acción de borrado masivo
        if not (request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'delete_selected'):
            queryset = queryset[:20]
        return queryset, use_distinct

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Agregar botón de nueva matrícula en la vista de edición"""
        extra_context = extra_context or {}
        extra_context['show_nueva_matricula'] = True
        extra_context['estudiante_id'] = object_id
        return super().change_view(request, object_id, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        bloqueados = {
            "tipo_identificacion", "sexo", "nacionalidad",
            "provincia", "canton", "distrito",
        }
        if db_field.name in bloqueados and not request.user.is_superuser:
            field.widget.can_add_related = False
            field.widget.can_change_related = False
        
        # Manejar el campo institución de manera especial
        if db_field.name == "institucion" and not request.user.is_superuser:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                field.initial = institucion_id
                field.widget.can_add_related = False
                field.widget.can_change_related = False
        
        return field
    
    def save_model(self, request, obj, form, change):
        # Forzar institución desde el contexto activo, ignorando el formulario
        institucion_id = getattr(request, 'institucion_activa_id', None)
        if not request.user.is_superuser and institucion_id:
            obj.institucion_id = institucion_id
        super().save_model(request, obj, form, change)

# ───────────────────────  Persona-Contacto admin  ───────────────────────
@admin.register(PersonaContacto)
class PersonaContactoAdmin(InstitucionScopedAdmin):
    form = PersonaContactoForm
    fields = None  # Fuerza el uso de fieldsets

    fieldsets = (
        ('Información Institucional', {
            'fields': ('institucion',),
            'classes': ('collapse',)
        }),
        ('Datos de la Persona de Contacto', {
            'fields': (
                'identificacion', 'primer_apellido', 'segundo_apellido', 'nombres',
                'celular_avisos', 'correo',
                'tipo_identificacion', 'estado_civil', 'escolaridad', 'ocupacion',
                'lugar_trabajo', 'telefono_trabajo',
            ),
        }),
    )

    list_display  = ("identificacion", "primer_apellido", "segundo_apellido", "nombres", "celular_avisos", "correo")
    search_fields = ("primer_apellido", "segundo_apellido", "nombres", "identificacion", "correo")
    list_filter   = ("institucion", "estado_civil", "ocupacion", "escolaridad")
    list_per_page = 25
    ordering = ("primer_apellido", "nombres")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Primero llamar al mixin para establecer el valor inicial
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        # Luego aplicar las restricciones específicas del admin
        bloqueados = {
            "institucion", "estado_civil", "escolaridad", "ocupacion",
        }
        if db_field.name in bloqueados and not request.user.is_superuser:
            field.widget.can_add_related = False
            field.widget.can_change_related = False
            if db_field.name == "institucion":
                field.disabled = True
                
                # Asegurar que el campo tenga el valor inicial correcto
                institucion_id = getattr(request, 'institucion_activa_id', None)
                if institucion_id and not field.initial:
                    field.initial = institucion_id
                    
        return field

# Eliminar los admin de Nivel, Seccion, Subgrupo y Periodo (ya están en sus apps)
# Mantener solo el admin de MatriculaAcademica

# ────────────────────────  Matrícula Académica admin  ───────────────────────────
@admin.register(MatriculaAcademica)
class MatriculaAcademicaAdmin(InstitucionScopedAdmin):
    form = MatriculaAcademicaForm
    
    class Media:
        js = (
            'admin/js/jquery.init.js',
            'matricula/js/dependent-especialidad.js',  # Forzar el JS correcto
            'matricula/js/clear-dependent-fields.js',  # Limpieza automática de campos dependientes
        )
    

    def get_list_display(self, request):
        """Mostrar institución solo para superusuarios"""
        base_display = ("identificacion_estudiante", "apellido1_estudiante", "apellido2_estudiante", "nombre_estudiante", "nivel", "curso_lectivo", "seccion", "subgrupo", "especialidad_nombre")
        if request.user.is_superuser:
            return base_display + ("institucion_estudiante",)
        return base_display
    def get_list_filter(self, request):
        """Mostrar filtro de institución solo para superusuarios"""
        base_filters = (NivelInstitucionFilter, SeccionInstitucionFilter, SubgrupoInstitucionFilter, CursoLectivoFilter, "estado", EspecialidadInstitucionFilter)
        if request.user.is_superuser:
            return base_filters + (InstitucionMatriculaFilter,)
        return base_filters
    search_fields = ("estudiante__identificacion", "estudiante__primer_apellido", "estudiante__nombres")
    ordering = ("curso_lectivo__anio", "estudiante__primer_apellido", "estudiante__nombres")
    
    # DAL maneja especialidad, seccion y subgrupo, autocomplete_fields para el resto
    autocomplete_fields = ("estudiante", "nivel")
    
    fields = ('estudiante', 'institucion', 'curso_lectivo', 'nivel', 'especialidad', 'seccion', 'subgrupo', 'estado')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Usuarios normales solo ven matrículas de su institución
        institucion_id = getattr(request, 'institucion_activa_id', None)
        if institucion_id:
            return qs.filter(estudiante__institucion_id=institucion_id)
        return qs.none()
    
    def identificacion_estudiante(self, obj):
        """Mostrar identificación del estudiante"""
        return obj.estudiante.identificacion
    identificacion_estudiante.short_description = "Identificación"
    identificacion_estudiante.admin_order_field = 'estudiante__identificacion'

    def apellido1_estudiante(self, obj):
        """Mostrar primer apellido del estudiante"""
        return obj.estudiante.primer_apellido
    apellido1_estudiante.short_description = "1er Apellido"
    apellido1_estudiante.admin_order_field = 'estudiante__primer_apellido'

    def apellido2_estudiante(self, obj):
        """Mostrar segundo apellido del estudiante"""
        return obj.estudiante.segundo_apellido
    apellido2_estudiante.short_description = "2do Apellido"
    apellido2_estudiante.admin_order_field = 'estudiante__segundo_apellido'

    def nombre_estudiante(self, obj):
        """Mostrar solo los nombres del estudiante"""
        return obj.estudiante.nombres
    nombre_estudiante.short_description = "Nombres"
    nombre_estudiante.admin_order_field = 'estudiante__nombres'

    def especialidad_nombre(self, obj):
        """Mostrar solo el nombre de la especialidad"""
        if obj.especialidad and hasattr(obj.especialidad, 'especialidad'):
            return obj.especialidad.especialidad.nombre
        return "-"
    especialidad_nombre.short_description = "Especialidad"
    especialidad_nombre.admin_order_field = 'especialidad__especialidad__nombre'

    def institucion_estudiante(self, obj):
        """Mostrar la institución del estudiante"""
        if obj.estudiante and hasattr(obj.estudiante, 'institucion'):
            return obj.estudiante.institucion.nombre
        return "-"
    institucion_estudiante.short_description = "Institución"
    institucion_estudiante.admin_order_field = 'estudiante__institucion__nombre'

    def get_form(self, request, obj=None, **kwargs):
        """Personalizar formulario para lógica inteligente de matrícula"""
        # Pasar el request al formulario a través de kwargs
        kwargs['form'] = MatriculaAcademicaForm
        Form = super().get_form(request, obj, **kwargs)
        
        # Crear una clase de formulario que incluya el request
        class FormWithRequest(Form):
            def __init__(self, *args, **kwargs):
                kwargs['request'] = request
                super().__init__(*args, **kwargs)
        
        form = FormWithRequest
        
        # Establecer estado por defecto para nuevas matrículas (valor de choice: 'activo')
        if not obj and 'estado' in form.base_fields:
            form.base_fields['estado'].initial = 'activo'
        
        # Si es una nueva matrícula (no obj) y hay estudiante en GET params
        if not obj and 'estudiante' in request.GET:
            try:
                from matricula.models import Estudiante
                estudiante_id = request.GET.get('estudiante')
                
                # Verificar que el estudiante pertenece a la institución del usuario
                if not request.user.is_superuser:
                    institucion_id = getattr(request, 'institucion_activa_id', None)
                    if institucion_id:
                        estudiante = Estudiante.objects.get(pk=estudiante_id, institucion_id=institucion_id)
                    else:
                        estudiante = Estudiante.objects.get(pk=estudiante_id)
                else:
                    estudiante = Estudiante.objects.get(pk=estudiante_id)
                
                # Buscar la ÚLTIMA matrícula activa del estudiante (por año más reciente)
                from matricula.models import MatriculaAcademica
                matricula_activa = MatriculaAcademica.objects.filter(
                    estudiante=estudiante,
                    estado__iexact='activo'
                ).order_by('-curso_lectivo__anio').first()
                
                if matricula_activa:
                    # Intentar obtener datos de siguiente matrícula
                    siguiente_data = MatriculaAcademica.get_siguiente_matricula_data(estudiante, matricula_activa.curso_lectivo)
                    
                    if siguiente_data:
                        # Pre-llenar campos con datos inteligentes
                        form.base_fields['estudiante'].initial = estudiante
                        form.base_fields['institucion'].initial = estudiante.institucion
                        form.base_fields['nivel'].initial = siguiente_data['nivel']
                        form.base_fields['curso_lectivo'].initial = siguiente_data['curso_lectivo']
                        if siguiente_data['especialidad']:
                            form.base_fields['especialidad'].initial = siguiente_data['especialidad']
                        
                        # Agregar mensaje informativo
                        form.base_fields['estudiante'].help_text = "Estudiante seleccionado automáticamente"
                        form.base_fields['nivel'].help_text = f"Nivel automático: {siguiente_data['nivel'].nombre}"
                        form.base_fields['curso_lectivo'].help_text = f"Curso automático: {siguiente_data['curso_lectivo'].nombre}"
                        if siguiente_data['especialidad']:
                            form.base_fields['especialidad'].help_text = f"Especialidad mantenida: {siguiente_data['especialidad'].nombre}"
                    else:
                        # Solo pre-llenar estudiante si no hay datos inteligentes
                        form.base_fields['estudiante'].initial = estudiante
                        form.base_fields['institucion'].initial = estudiante.institucion
                        form.base_fields['estudiante'].help_text = "Estudiante seleccionado. Complete manualmente los demás campos."
                else:
                    # Solo pre-llenar estudiante, proceso completamente manual
                    form.base_fields['estudiante'].initial = estudiante
                    form.base_fields['institucion'].initial = estudiante.institucion
                    form.base_fields['estudiante'].help_text = "Estudiante seleccionado. Complete manualmente nivel, curso lectivo y demás campos."
                        
            except (Estudiante.DoesNotExist, ValueError):
                pass
        
        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        bloqueados = {"estudiante", "nivel"}  # especialidad, seccion y subgrupo las maneja DAL
        if db_field.name in bloqueados and not request.user.is_superuser:
            field.widget.can_add_related = False
            field.widget.can_change_related = False
        
        # Configurar límite de 44 elementos para evitar sobrecargar los selects
        # Considerando que los grupos son máximo de 40 estudiantes
        if db_field.name in ["seccion", "subgrupo"]:
            # Limitar a máximo 44 elementos para secciones y subgrupos
            if "queryset" not in kwargs:
                kwargs["queryset"] = db_field.related_model.objects.all()
            kwargs["queryset"] = kwargs["queryset"][:44]
        
        # DAL maneja el filtrado de especialidad, seccion y subgrupo automáticamente
        return field

    def get_search_results(self, request, queryset, search_term):
        """Limitar resultados de búsqueda para evitar sobrecargar los selects"""
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        
        # Limitar a máximo 44 resultados para evitar sobrecargar la interfaz
        # Considerando que los grupos son máximo de 40 estudiantes
        if queryset.count() > 44:
            queryset = queryset[:44]
        
        return queryset, use_distinct

@admin.register(PlantillaImpresionMatricula)
class PlantillaImpresionMatriculaAdmin(admin.ModelAdmin):
    list_display = ['institucion', 'titulo']
    list_filter = ['institucion']
    search_fields = ['institucion__nombre', 'titulo']
    
    fieldsets = (
        ('Información de la Institución', {
            'fields': ('institucion',)
        }),
        ('Contenido de la Plantilla', {
            'fields': ('titulo', 'logo_mep', 'encabezado', 'pie_pagina')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        else:
            # Usuario normal: solo ver plantillas de su institución
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                return qs.filter(institucion_id=institucion_id)
            return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "institucion" and not request.user.is_superuser:
            # Usuario normal: solo puede seleccionar su institución activa
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                kwargs["queryset"] = Institucion.objects.filter(id=institucion_id)
                kwargs["initial"] = institucion_id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
