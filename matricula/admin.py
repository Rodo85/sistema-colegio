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

# ─────────────────────────────  Formularios  ────────────────────────────
class EstudianteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'provincia' in self.fields and not self.instance.pk:
            primera_provincia = Provincia.objects.first()
            if primera_provincia:
                self.fields['provincia'].initial = primera_provincia.id

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
        fields = "__all__"
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
        # Datos Personales (incluye tipo_estudiante y los de contacto al final)
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
        list_display = list(super().get_list_display(request))
        if 'acciones' not in list_display:
            list_display.append('acciones')
        return list_display

    def acciones(self, obj):
        """Enlaces de acción para cada estudiante"""
        if obj.pk:
            return format_html(
                '<a class="button" href="{}">📚 Matrícula</a>',
                f'/admin/matricula/matriculaacademica/add/?estudiante={obj.pk}'
            )
        return ""
    acciones.short_description = "Acciones"



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

    # Lista sin foto (más limpia)
    list_display = ("identificacion", "primer_apellido", "segundo_apellido", "nombres", "tipo_estudiante")
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

    def get_form(self, request, obj=None, **kwargs):
        """Personalizar etiquetas de campos"""
        form = super().get_form(request, obj, **kwargs)
        if form.base_fields.get('sexo'):
            form.base_fields['sexo'].label = "Género"
        return form

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Agregar botón de nueva matrícula en la vista de edición"""
        extra_context = extra_context or {}
        extra_context['show_nueva_matricula'] = True
        extra_context['estudiante_id'] = object_id
        return super().change_view(request, object_id, form_url, extra_context)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        bloqueados = {
            "institucion", "tipo_identificacion", "sexo", "nacionalidad",
            "provincia", "canton", "distrito",
        }
        if db_field.name in bloqueados and not request.user.is_superuser:
            field.widget.can_add_related = False
            field.widget.can_change_related = False
            if db_field.name == "institucion":
                field.disabled = True
        return field

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
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        bloqueados = {
            "institucion", "estado_civil", "escolaridad", "ocupacion",
        }
        if db_field.name in bloqueados and not request.user.is_superuser:
            field.widget.can_add_related = False
            field.widget.can_change_related = False
            if db_field.name == "institucion":
                field.disabled = True
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
    

    list_display = ("identificacion_estudiante", "nombre_estudiante", "nivel", "seccion", "subgrupo", "curso_lectivo", "estado", "especialidad_nombre", "fecha_asignacion")
    list_filter = ("nivel", "seccion", "subgrupo", "curso_lectivo", "estado", "especialidad")
    search_fields = ("estudiante__identificacion", "estudiante__primer_apellido", "estudiante__nombres")
    ordering = ("curso_lectivo__anio", "estudiante__primer_apellido", "estudiante__nombres")
    
    # DAL maneja especialidad, seccion y subgrupo, autocomplete_fields para el resto
    autocomplete_fields = ("estudiante", "nivel")
    
    fields = ('estudiante', 'curso_lectivo', 'nivel', 'especialidad', 'seccion', 'subgrupo', 'estado')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Usuarios normales solo ven matrículas de su institución
        return qs.filter(estudiante__institucion=request.institucion_activa_id)
    
    def identificacion_estudiante(self, obj):
        """Mostrar identificación del estudiante"""
        return obj.estudiante.identificacion
    identificacion_estudiante.short_description = "Identificación"
    identificacion_estudiante.admin_order_field = 'estudiante__identificacion'

    def nombre_estudiante(self, obj):
        """Mostrar nombre completo del estudiante"""
        return f"{obj.estudiante.primer_apellido} {obj.estudiante.nombres}"
    nombre_estudiante.short_description = "Nombre"
    nombre_estudiante.admin_order_field = 'estudiante__primer_apellido'

    def especialidad_nombre(self, obj):
        """Mostrar solo el nombre de la especialidad"""
        if obj.especialidad and hasattr(obj.especialidad, 'especialidad'):
            return obj.especialidad.especialidad.nombre
        return "-"
    especialidad_nombre.short_description = "Especialidad"
    especialidad_nombre.admin_order_field = 'especialidad__especialidad__nombre'

    def get_form(self, request, obj=None, **kwargs):
        """Personalizar formulario para lógica inteligente de matrícula"""
        form = super().get_form(request, obj, **kwargs)
        
        # Establecer estado por defecto para nuevas matrículas (valor de choice: 'activo')
        if not obj and 'estado' in form.base_fields:
            form.base_fields['estado'].initial = 'activo'
        
        # Si es una nueva matrícula (no obj) y hay estudiante en GET params
        if not obj and 'estudiante' in request.GET:
            try:
                from matricula.models import Estudiante
                estudiante_id = request.GET.get('estudiante')
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
                        form.base_fields['estudiante'].help_text = "Estudiante seleccionado. Complete manualmente los demás campos."
                else:
                    # Solo pre-llenar estudiante, proceso completamente manual
                    form.base_fields['estudiante'].initial = estudiante
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
        
        # DAL maneja el filtrado de especialidad, seccion y subgrupo automáticamente
        return field

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
