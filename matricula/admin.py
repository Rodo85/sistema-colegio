import unicodedata

from django import forms
from django.contrib import admin, messages
from django.db.models import F, Q, Value
from django.db.models.functions import Replace, Upper
from django.forms.models import BaseInlineFormSet
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from core.mixins import InstitucionScopedAdmin
from .models import Estudiante, EncargadoEstudiante, PersonaContacto, MatriculaAcademica, PlantillaImpresionMatricula, AsignacionGrupos, EstudianteInstitucion

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
            return queryset.filter(
                estudiante__instituciones_estudiante__institucion_id=self.value(),
                estudiante__instituciones_estudiante__estado='activo'
            )
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
    
    # Forzar a que el filtro siempre se muestre en la UI (Jazzmin respeta has_output)
    def has_output(self):
        return True

    def lookups(self, request, model_admin):
        from config_institucional.models import EspecialidadCursoLectivo
        from catalogos.models import CursoLectivo
        import datetime
        
        # Determinar curso lectivo de contexto
        curso_lectivo_id = request.GET.get('curso_lectivo')
        if not curso_lectivo_id:
            curso_actual = CursoLectivo.objects.filter(
                anio=datetime.date.today().year
            ).first()
            curso_lectivo_id = curso_actual.id if curso_actual else None
        
        if not curso_lectivo_id:
            # Si no hay curso lectivo determinable, mantener el filtro visible
            # pero sin opciones (evita que desaparezca en Jazzmin)
            return [(-1, '—')]
        
        if request.user.is_superuser:
            qs = EspecialidadCursoLectivo.objects.filter(
                curso_lectivo_id=curso_lectivo_id
            )
        else:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if not institucion_id:
                return [(-1, '—')]
            qs = EspecialidadCursoLectivo.objects.filter(
                institucion_id=institucion_id,
                curso_lectivo_id=curso_lectivo_id
            )
        opciones = list(qs.values_list('especialidad__id', 'especialidad__nombre').distinct())
        # Garantizar que el valor actualmente seleccionado siga disponible
        seleccionado = request.GET.get(self.parameter_name)
        if seleccionado and str(seleccionado).isdigit():
            seleccionado = int(seleccionado)
            ids_presentes = {oid for (oid, _nombre) in opciones}
            if seleccionado not in ids_presentes:
                try:
                    from catalogos.models import Especialidad
                    esp = Especialidad.objects.get(id=seleccionado)
                    opciones.append((esp.id, esp.nombre))
                except Exception:
                    pass
        # Asegurar al menos una opción para que el filtro no se oculte
        if not opciones:
            return [(-1, '—')]
        return opciones

    def queryset(self, request, queryset):
        valor = self.value()
        if valor and str(valor).isdigit() and int(valor) > 0:
            # Filtrar por la especialidad REAL (catalogos.Especialidad) a través del ECL
            return queryset.filter(especialidad__especialidad_id=valor)
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
        # Si no hay filtro seleccionado, mostrar TODAS las matrículas de todos los años
        return queryset

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

        # Forzar checkbox en campos tri-estado (evitar NullBoolean select)
        for nombre in ('presenta_enfermedad', 'orden_alejamiento'):
            if nombre in self.fields:
                etiqueta = self.fields[nombre].label
                valor_inicial = False
                if getattr(self.instance, 'pk', None) is not None:
                    valor = getattr(self.instance, nombre, None)
                    valor_inicial = bool(valor) if valor is not None else False
                self.fields[nombre] = forms.BooleanField(
                    required=False,
                    label=etiqueta,
                    initial=valor_inicial,
                    widget=forms.CheckboxInput()
                )

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
        
        # NOTA: La validación de unicidad se maneja en el modelo Estudiante.clean()
        # No validamos aquí para evitar duplicar lógica
        
        # Manejar eliminación de foto si el checkbox está marcado
        foto_clear = self.data.get('foto-clear')
        if foto_clear:
            # Si el checkbox está marcado, eliminar la foto
            cleaned_data['foto'] = None
        
        if foto and hasattr(foto, 'size'):
            try:
                foto_size = foto.size
            except (FileNotFoundError, OSError):
                # El archivo físico no existe; informar al usuario para que vuelva a subirlo
                cleaned_data['foto'] = None
                self.add_error('foto', 'La foto asociada ya no existe en el servidor. Vuelve a subirla.')
                foto_size = None
            if foto_size is not None:
                # Verificar tamaño del archivo (máximo 5MB)
                if foto_size > 5 * 1024 * 1024:  # 5MB en bytes
                    self.add_error('foto', 'La imagen no puede ser mayor a 5MB.')
                
                # Verificar tipo de archivo
                allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
                if hasattr(foto, 'content_type') and foto.content_type not in allowed_types:
                    self.add_error('foto', 'Solo se permiten archivos de imagen (JPG, PNG, GIF).')
        
        # Normalizar los booleanos tri-estado para que nunca queden en None
        for nombre in ('presenta_enfermedad', 'orden_alejamiento'):
            cleaned_data[nombre] = bool(cleaned_data.get(nombre, False))

        return cleaned_data

    class Meta:
        model = Estudiante
        # Incluir todos los campos; la lógica de ocultar/forzar institución
        # para usuarios no superusuarios se maneja en get_form
        fields = '__all__'
        widgets = {
            'provincia': forms.Select(attrs={'id': 'id_provincia'}),
            'canton': forms.Select(attrs={'id': 'id_canton'}),
            'distrito': forms.Select(attrs={'id': 'id_distrito'}),
            'identificacion': forms.TextInput(attrs={
                'autocomplete': 'off',
                'placeholder': "Si es cédula de identidad no ingrese guiones. Ejemplo: 914750521",
                'title': 'Ingrese 9 dígitos sin guiones ni espacios',
                'id': 'id_identificacion',
                'class': 'vTextField',
                'style': 'display: inline-block; width: 60%;'
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
            "matricula/js/buscar-estudiante-existente.js",
        )

class PersonaContactoForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        tipo_identificacion = cleaned_data.get('tipo_identificacion')
        identificacion = cleaned_data.get('identificacion')
        institucion = cleaned_data.get('institucion')
        
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
        
        # Validar unicidad de identificación por institución
        if institucion and identificacion:
            identificacion_normalizada = identificacion.strip().upper()
            contactos_existentes = PersonaContacto.objects.filter(
                institucion=institucion,
                identificacion=identificacion_normalizada
            )
            
            # Excluir el contacto actual si está editando
            if self.instance and self.instance.pk:
                contactos_existentes = contactos_existentes.exclude(pk=self.instance.pk)
            
            if contactos_existentes.exists():
                contacto_existente = contactos_existentes.first()
                segundo_apellido = f" {contacto_existente.segundo_apellido}" if contacto_existente.segundo_apellido else ""
                self.add_error('identificacion', 
                    f'Ya existe una persona de contacto con la identificación {identificacion_normalizada} en esta institución: '
                    f'{contacto_existente.primer_apellido}{segundo_apellido} {contacto_existente.nombres}.')
        
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
class EncargadoInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        principal_count = 0
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            if form.cleaned_data.get('principal'):
                principal_count += 1
        if principal_count > 1:
            raise forms.ValidationError('Solo puede haber un encargado principal por estudiante.')

class EncargadoInline(admin.TabularInline):
    model = EncargadoEstudiante
    extra = 0
    fields = ("persona_contacto", "parentesco", "convivencia", "principal")
    readonly_fields = ()
    formset = EncargadoInlineFormSet
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parentesco":
            from catalogos.models import Parentesco
            from django.db.models import Case, When, Value, IntegerField
            
            # Ordenar con prioridad: Madre, Padre, Encargado(a), luego alfabético
            parentescos = Parentesco.objects.annotate(
                orden=Case(
                    When(descripcion__iexact='MADRE', then=Value(1)),
                    When(descripcion__iexact='PADRE', then=Value(2)),
                    When(descripcion__iexact='ENCARGADO(A)', then=Value(3)),
                    When(descripcion__iexact='ENCARGADO', then=Value(3)),
                    When(descripcion__iexact='ENCARGADA', then=Value(3)),
                    default=Value(999),
                    output_field=IntegerField()
                )
            ).order_by('orden', 'descripcion')
            
            kwargs["queryset"] = parentescos
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class EstudianteInstitucionInline(admin.TabularInline):
    model = EstudianteInstitucion
    extra = 1
    fields = ("estudiante_identificacion", "institucion", "estado", "fecha_ingreso", "fecha_salida", "observaciones")
    readonly_fields = ("fecha_registro", "estudiante_identificacion")
    
    def estudiante_identificacion(self, obj):
        """Mostrar la identificación del estudiante"""
        if obj.estudiante:
            return obj.estudiante.identificacion
        return "-"
    estudiante_identificacion.short_description = "Identificación"
    
    def get_readonly_fields(self, request, obj=None):
        # Solo superusuarios pueden editar institución
        if not request.user.is_superuser:
            return self.readonly_fields + ("institucion",)
        return self.readonly_fields
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "institucion" and not request.user.is_superuser:
            # Usuarios normales solo pueden agregar a su institución activa
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                kwargs["queryset"] = Institucion.objects.filter(id=institucion_id)
                kwargs["initial"] = institucion_id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class MatriculaAcademicaInline(admin.StackedInline):  # Cambiado a StackedInline para vista vertical
    model = MatriculaAcademica
    form = MatriculaAcademicaForm
    extra = 0
    fields = ('curso_lectivo', 'nivel', 'seccion', 'subgrupo', 'estado', 'especialidad')
    # Permitir histórico, no forzar matrícula inmediata
    # Validación de matrícula activa se moverá al modelo
    
    def get_fields(self, request, obj=None):
        """
        Filtrar campos según permisos del usuario.
        Los campos seccion, subgrupo y estado solo se muestran si el usuario tiene el permiso correspondiente.
        """
        fields = list(super().get_fields(request, obj))
        
        # Si no es superusuario y no tiene el permiso específico, ocultar seccion, subgrupo y estado
        if not request.user.is_superuser:
            if not request.user.has_perm('matricula.manage_seccion_subgrupo_estado'):
                # Remover los campos restringidos
                campos_restringidos = ['seccion', 'subgrupo', 'estado']
                fields = [f for f in fields if f not in campos_restringidos]
        
        return fields
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Filtrar el queryset de curso_lectivo para mostrar solo el curso con matricular=True
        """
        if db_field.name == "curso_lectivo":
            from catalogos.models import CursoLectivo
            # Filtrar para mostrar solo el curso marcado para matrícula
            curso_matricular = CursoLectivo.get_matricular()
            if curso_matricular:
                kwargs["queryset"] = CursoLectivo.objects.filter(id=curso_matricular.id)
            else:
                # Si no hay curso marcado para matrícula, mostrar todos
                kwargs["queryset"] = CursoLectivo.objects.all()
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    class Media:
        js = (
            'admin/js/jquery.init.js',
            'matricula/js/dependent-especialidad.js',  # Para inlines también
            'matricula/js/clear-dependent-fields.js',  # Limpieza automática de campos dependientes
            'matricula/js/especialidad-limpia-campos.js',  # Limpieza específica al cambiar especialidad
        )

# ────────────────────────  Estudiante admin  ───────────────────────────
@admin.register(Estudiante)
class EstudianteAdmin(InstitucionScopedAdmin):
    ACCENT_REPLACEMENTS = (
        ("Á", "A"), ("À", "A"), ("Â", "A"), ("Ã", "A"), ("Ä", "A"),
        ("É", "E"), ("È", "E"), ("Ê", "E"), ("Ë", "E"),
        ("Í", "I"), ("Ì", "I"), ("Î", "I"), ("Ï", "I"),
        ("Ó", "O"), ("Ò", "O"), ("Ô", "O"), ("Õ", "O"), ("Ö", "O"),
        ("Ú", "U"), ("Ù", "U"), ("Û", "U"), ("Ü", "U"),
        ("Ñ", "N"), ("Ç", "C"),
    )

    @staticmethod
    def _normalize_text(value):
        if value is None:
            return ""
        normalized = unicodedata.normalize("NFD", value.upper())
        return "".join(char for char in normalized if unicodedata.category(char) != "Mn")

    def _normalize_expression(self, field_name):
        expression = Upper(F(field_name))
        for source, target in self.ACCENT_REPLACEMENTS:
            expression = Replace(expression, Value(source), Value(target))
        return expression

    def _annotate_normalized_fields(self, queryset):
        annotations = {}
        aliases = {}
        for field in self.search_fields:
            alias = f"_norm_{field.replace('__', '_')}"
            if alias in annotations:
                continue
            annotations[alias] = self._normalize_expression(field)
            aliases[field] = alias
        if annotations:
            queryset = queryset.annotate(**annotations)
        return queryset, list(aliases.values())

    def _apply_accent_insensitive_filter(self, queryset, search_term, lookups=None):
        if not search_term:
            return queryset.none()
        lookups = lookups or ["contains"]
        normalized_term = self._normalize_text(search_term)
        queryset, aliases = self._annotate_normalized_fields(queryset)
        q_objects = Q()
        for alias in aliases:
            for lookup in lookups:
                q_objects |= Q(**{f"{alias}__{lookup}": normalized_term})
        return queryset.filter(q_objects)

    form    = EstudianteForm
    inlines = [EncargadoInline]  # Quitado EstudianteInstitucionInline
    fields = None  # Fuerza el uso de fieldsets

    def get_fieldsets(self, request, obj=None):
        fieldsets = []
        # Ya no hay campo institucion en Estudiante (se maneja via EstudianteInstitucion)
        # Usuarios normales: no incluir campo institucion en el formulario
        fieldsets.append(
            ('Datos Personales', {
                'fields': (
                    'tipo_identificacion', 'identificacion',
                    'tipo_estudiante',
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

        # Plan Nacional (se muestra solo cuando tipo_estudiante = PN)
        fieldsets.append(
            ('Plan Nacional', {
                'fields': (
                    'posee_carnet_conapdis',
                    'posee_valvula_drenaje_lcr',
                    'usa_apoyo', 'apoyo_cual',
                    'tipo_condicion_diagnosticada', 'tipo_condicion_otro',
                    'posee_control', 'control_cual',
                    'orden_alejamiento', 'orden_alejamiento_nombre',
                ),
                'classes': ('plannacional-section',)
            })
        )
        return fieldsets

    def get_list_display(self, request):
        """Agregar enlaces de acción personalizados"""
        # Guardar el request para usarlo en acciones
        self._request = request
        base_display = ("identificacion", "primer_apellido", "segundo_apellido", "nombres", "tipo_estudiante", "acciones")
        return base_display

    def get_list_display_links(self, request, list_display):
        """Evitar que las filas sean clicables si el usuario solo puede ver."""
        if request.user.is_superuser or request.user.has_perm('matricula.change_estudiante'):
            # Enlazar a los campos principales cuando tiene permiso de cambiar
            return ("identificacion", "primer_apellido", "segundo_apellido", "nombres")
        # Sin enlaces para evitar navegación al change_view (evita 403)
        return ()

    def acciones(self, obj):
        """Enlaces de acción para cada estudiante"""
        # Mostrar el botón solo si el usuario puede crear matrículas
        req = getattr(self, '_request', None)
        if req and not (req.user.is_superuser or req.user.has_perm('matricula.add_matriculaacademica')):
            return ""
        if obj.pk:
            # Obtener la URL del admin de matrícula
            from django.urls import reverse
            try:
                url = reverse('admin:matricula_matriculaacademica_add')
                url += f'?estudiante={obj.pk}'
                # Si tenemos el request guardado y no es superusuario, agregar la institución
                if req and not req.user.is_superuser:
                    institucion_id = getattr(req, 'institucion_activa_id', None)
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
        # Si el usuario no tiene permiso de cambio, todos los campos en solo lectura
        if not request.user.has_perm('matricula.change_estudiante') and not request.user.is_superuser:
            # Devolver todos los fields del modelo como read-only
            return [f.name for f in Estudiante._meta.get_fields() if hasattr(f, 'attname')]
        return super().get_readonly_fields(request, obj)
    
    def get_form(self, request, obj=None, **kwargs):
        """Personalizar el formulario según el usuario."""
        Form = super().get_form(request, obj, **kwargs)
        
        class FormCustom(Form):
            def __init__(self, *args, **kw):
                super().__init__(*args, **kw)
                # Etiqueta personalizada
                if self.base_fields.get('sexo'):
                    self.base_fields['sexo'].label = "Género"

        return FormCustom

    # Búsqueda por identificación y nombre
    search_fields = ("identificacion", "primer_apellido", "segundo_apellido", "nombres")
    # Filtros incluyendo foto
    list_filter = ('tipo_estudiante', 'sexo', 'nacionalidad')
    list_per_page = 25
    ordering = ("primer_apellido", "nombres")
    
    def get_list_filter(self, request):
        """Ocultar filtros para usuarios con permiso 'only_search_estudiante'"""
        if request.user.has_perm('matricula.only_search_estudiante'):
            return ()  # Sin filtros
        return self.list_filter
    
    def get_queryset(self, request):
        """Filtrar estudiantes por institución activa usando EstudianteInstitucion"""
        qs = super(InstitucionScopedAdmin, self).get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        # Filtrar por institución activa a través de EstudianteInstitucion
        institucion_id = getattr(request, 'institucion_activa_id', None)
        if institucion_id:
            qs = qs.filter(
                instituciones_estudiante__institucion_id=institucion_id,
                instituciones_estudiante__estado='activo'
            ).distinct()
        else:
            return qs.none()
        
        # Si el usuario tiene el permiso de "solo búsqueda", no mostrar nada por defecto
        if request.user.has_perm('matricula.only_search_estudiante'):
            # Verificar si hay término de búsqueda
            search_term = request.GET.get('q', '').strip()
            if not search_term:
                # No hay búsqueda, retornar queryset vacío
                resolver = getattr(request, 'resolver_match', None)
                if resolver and resolver.kwargs.get('object_id'):
                    return qs
                return qs.none()
        
        return qs

    def get_search_results(self, request, queryset, search_term):
        base_queryset = queryset

        if request.user.has_perm('matricula.only_search_estudiante') and search_term:
            queryset = self._apply_accent_insensitive_filter(
                base_queryset, search_term, lookups=["startswith", "endswith", "contains"]
            ).distinct()

            if not (request.method == 'POST' and request.POST.get('action') == 'delete_selected'):
                queryset = queryset[:20]

            return queryset, False

        queryset, use_distinct = super().get_search_results(request, queryset, search_term)

        if search_term:
            accent_queryset = self._apply_accent_insensitive_filter(
                base_queryset, search_term, lookups=["contains", "startswith", "endswith"]
            )
            queryset = (queryset | accent_queryset).distinct()
            use_distinct = True

        return queryset, use_distinct

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Agregar botón de nueva matrícula solo si el usuario puede crearla."""
        extra_context = extra_context or {}
        can_add_matricula = request.user.has_perm('matricula.add_matriculaacademica')
        extra_context['show_nueva_matricula'] = bool(can_add_matricula)
        extra_context['estudiante_id'] = object_id
        return super().change_view(request, object_id, form_url, extra_context)

    def response_change(self, request, obj):
        if "_continuar_matricula" in request.POST:
            url = reverse('admin:matricula_matriculaacademica_add')
            url += f"?estudiante={obj.pk}"
            if not request.user.is_superuser:
                institucion_id = getattr(request, 'institucion_activa_id', None)
                if institucion_id:
                    url += f"&_institucion={institucion_id}"
            self.message_user(
                request,
                "Estudiante guardado correctamente. Continúa con la matrícula.",
                level=messages.SUCCESS,
            )
            return redirect(url)
        return super().response_change(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        bloqueados = {
            "tipo_identificacion", "sexo", "nacionalidad",
            "provincia", "canton", "distrito",
        }
        if db_field.name in bloqueados and not request.user.is_superuser:
            field.widget.can_add_related = False
            field.widget.can_change_related = False
        
        return field
    
    def save_model(self, request, obj, form, change):
        # Manejar eliminación de foto si el checkbox está marcado
        foto_clear = request.POST.get('foto-clear')
        if foto_clear and obj.foto:
            # Eliminar el archivo físico de la foto
            import os
            try:
                if os.path.isfile(obj.foto.path):
                    os.remove(obj.foto.path)
            except Exception:
                pass  # Ignorar errores al eliminar el archivo
            # Limpiar el campo foto del objeto
            obj.foto = None
        
        # Guardar el estudiante primero
        super().save_model(request, obj, form, change)
        
        # Si es creación (no edición) y usuario NO es superusuario
        # Crear automáticamente la relación EstudianteInstitucion
        if not change and not request.user.is_superuser:
            from django.utils import timezone
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                # Verificar que no existe ya una relación activa
                if not EstudianteInstitucion.objects.filter(
                    estudiante=obj,
                    institucion_id=institucion_id,
                    estado='activo'
                ).exists():
                    fecha_actual = timezone.now().date()
                    EstudianteInstitucion.objects.create(
                        estudiante=obj,
                        institucion_id=institucion_id,
                        estado='activo',
                        fecha_ingreso=fecha_actual,
                        usuario_registro=request.user,
                        observaciones=f'Estudiante creado el {fecha_actual.strftime("%d/%m/%Y")} por {request.user.full_name() or request.user.email}'
                    )
    
    def has_change_permission(self, request, obj=None):
        """Deshabilitar edición de estudiantes dados de baja"""
        # Verificar permiso base primero
        if not super().has_change_permission(request, obj):
            return False
        
        # Si no hay objeto específico, permitir (para el listado)
        if obj is None:
            return True
        
        # Superusuario siempre puede editar
        if request.user.is_superuser:
            return True
        
        # Verificar si el estudiante está dado de baja en la institución del usuario
        institucion_id = getattr(request, 'institucion_activa_id', None)
        if institucion_id:
            relacion = EstudianteInstitucion.objects.filter(
                estudiante=obj,
                institucion_id=institucion_id
            ).first()
            
            if relacion and relacion.estado != 'activo':
                # Estudiante dado de baja, no permitir edición
                return False
        
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Deshabilitar eliminación de estudiantes dados de baja"""
        # Verificar permiso base primero
        if not super().has_delete_permission(request, obj):
            return False
        
        # Si no hay objeto específico, permitir (para el listado)
        if obj is None:
            return True
        
        # Superusuario siempre puede eliminar
        if request.user.is_superuser:
            return True
        
        # Verificar si el estudiante está dado de baja en la institución del usuario
        institucion_id = getattr(request, 'institucion_activa_id', None)
        if institucion_id:
            relacion = EstudianteInstitucion.objects.filter(
                estudiante=obj,
                institucion_id=institucion_id
            ).first()
            
            if relacion and relacion.estado != 'activo':
                # Estudiante dado de baja, no permitir eliminación
                return False
        
        return True
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Agregar mensaje de advertencia si el estudiante está dado de baja"""
        if object_id:
            obj = self.get_object(request, object_id)
            if obj and not request.user.is_superuser:
                institucion_id = getattr(request, 'institucion_activa_id', None)
                if institucion_id:
                    relacion = EstudianteInstitucion.objects.filter(
                        estudiante=obj,
                        institucion_id=institucion_id
                    ).first()
                    
                    if relacion and relacion.estado != 'activo':
                        messages.warning(
                            request,
                            f'Este estudiante está dado de baja (Estado: {relacion.get_estado_display()}). '
                            f'Solo puede consultar su información, no puede modificarla.'
                        )
        
        return super().changeform_view(request, object_id, form_url, extra_context)
    
    class Media:
        js = (
            'admin/js/jquery.init.js',
            'matricula/js/dependent-dropdowns.js',  # Provincia > Cantón > Distrito
            'matricula/js/toggle-plan-nacional.js',  # Mostrar/ocultar pestaña Plan Nacional
        )

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
                'tipo_identificacion', 'identificacion',
                'primer_apellido', 'segundo_apellido', 'nombres',
                'celular_avisos', 'correo',
                'estado_civil', 'escolaridad', 'ocupacion',
                'lugar_trabajo', 'telefono_trabajo',
            ),
        }),
    )

    list_display  = ("identificacion", "primer_apellido", "segundo_apellido", "nombres", "celular_avisos", "correo")
    search_fields = ("primer_apellido", "segundo_apellido", "nombres", "identificacion", "correo")
    list_filter   = ("institucion", "estado_civil", "ocupacion", "escolaridad")
    list_per_page = 25
    ordering = ("primer_apellido", "nombres")

    def get_list_filter(self, request):
        """Ocultar filtros cuando el usuario solo puede buscar contactos."""
        if request.user.has_perm('matricula.only_search_personacontacto'):
            return ()
        return self.list_filter

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        # Para el permiso especial, no mostrar nada a menos que use búsqueda
        if request.user.has_perm('matricula.only_search_personacontacto'):
            search_term = request.GET.get('q', '').strip()
            if not search_term:
                resolver = getattr(request, 'resolver_match', None)
                if resolver and resolver.kwargs.get('object_id'):
                    return qs
                return qs.none()

        return qs

    def get_search_results(self, request, queryset, search_term):
        # Manejo especial para el permiso de búsqueda
        if request.user.has_perm('matricula.only_search_personacontacto') and search_term:
            from django.db.models import Q

            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f"{field}__istartswith": search_term})
                q_objects |= Q(**{f"{field}__iendswith": search_term})

            queryset = queryset.filter(q_objects)

            if not (request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'delete_selected'):
                queryset = queryset[:20]

            # devolvemos False para que Django no intente aplicar distinct automáticamente
            return queryset, False

        return super().get_search_results(request, queryset, search_term)

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
    change_form_template = "admin/matricula/matriculaacademica/change_form.html"
    
    class Media:
        js = (
            'admin/js/jquery.init.js',
            'matricula/js/dependent-especialidad.js',  # Forzar el JS correcto
            'matricula/js/clear-dependent-fields.js',  # Limpieza automática de campos dependientes
            'matricula/js/especialidad-limpia-campos.js',  # Limpieza específica al cambiar especialidad
            'matricula/js/persist-admin-filters.js',   # Fix visual Jazzmin: no ocultar selects
        )
    

    def get_list_display(self, request):
        """Mostrar columnas según permisos del usuario"""
        base_display = ["identificacion_estudiante", "apellido1_estudiante", "apellido2_estudiante", "nombre_estudiante", "nivel", "curso_lectivo", "seccion", "subgrupo", "especialidad_nombre"]
        
        # Si no es superusuario y no tiene el permiso, ocultar seccion y subgrupo de la lista
        if not request.user.is_superuser:
            if not request.user.has_perm('matricula.manage_seccion_subgrupo_estado'):
                # Remover seccion y subgrupo de la vista de lista
                base_display = [f for f in base_display if f not in ['seccion', 'subgrupo']]
        
        if request.user.is_superuser:
            return tuple(base_display) + ("institucion_estudiante",)
        return tuple(base_display)
    def get_list_filter(self, request):
        """Mostrar filtros según permisos del usuario"""
        # Usar nuestro filtro personalizado que no depende del queryset
        base_filters = [
            NivelInstitucionFilter,
            'nivel',
            SeccionInstitucionFilter,
            SubgrupoInstitucionFilter,
            CursoLectivoFilter,
            "estado",
            EspecialidadInstitucionFilter,
        ]
        
        # Si no es superusuario y no tiene el permiso, ocultar filtros de seccion, subgrupo y estado
        if not request.user.is_superuser:
            if not request.user.has_perm('matricula.manage_seccion_subgrupo_estado'):
                # Remover los filtros restringidos
                base_filters = [f for f in base_filters if f not in [SeccionInstitucionFilter, SubgrupoInstitucionFilter, 'estado']]
        
        if request.user.is_superuser:
            return tuple(base_filters) + (InstitucionMatriculaFilter,)
        return tuple(base_filters)
    search_fields = ("estudiante__identificacion", "estudiante__primer_apellido", "estudiante__nombres")
    ordering = ("curso_lectivo__anio", "estudiante__primer_apellido", "estudiante__nombres")
    
    # DAL maneja especialidad, seccion y subgrupo, autocomplete_fields para el resto
    autocomplete_fields = ("estudiante", "nivel")
    
    # Campos base - se filtrarán dinámicamente en get_fields()
    fields = ('estudiante', 'institucion', 'curso_lectivo', 'nivel', 'especialidad', 'seccion', 'subgrupo', 'estado')
    
    def get_fields(self, request, obj=None):
        """
        Filtrar campos según permisos del usuario.
        Los campos seccion, subgrupo y estado solo se muestran si el usuario tiene el permiso correspondiente.
        """
        fields = list(super().get_fields(request, obj))
        
        # Si no es superusuario y no tiene el permiso específico, ocultar seccion, subgrupo y estado
        if not request.user.is_superuser:
            if not request.user.has_perm('matricula.manage_seccion_subgrupo_estado'):
                # Remover los campos restringidos
                campos_restringidos = ['seccion', 'subgrupo', 'estado']
                fields = [f for f in fields if f not in campos_restringidos]
        
        return fields
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Filtrar el queryset de curso_lectivo para mostrar solo el curso con matricular=True
        """
        if db_field.name == "curso_lectivo":
            from catalogos.models import CursoLectivo
            # Filtrar para mostrar solo el curso marcado para matrícula
            curso_matricular = CursoLectivo.get_matricular()
            if curso_matricular:
                kwargs["queryset"] = CursoLectivo.objects.filter(id=curso_matricular.id)
            else:
                # Si no hay curso marcado para matrícula, mostrar todos
                kwargs["queryset"] = CursoLectivo.objects.all()
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Usuarios normales solo ven matrículas de su institución
        # El estudiante usa una tabla intermedia EstudianteInstitucion
        institucion_id = getattr(request, 'institucion_activa_id', None)
        if institucion_id:
            return qs.filter(
                estudiante__instituciones_estudiante__institucion_id=institucion_id,
                estudiante__instituciones_estudiante__estado='activo'
            )
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
        if obj.estudiante:
            institucion_activa = obj.estudiante.get_institucion_activa()
            if institucion_activa:
                return institucion_activa.nombre
        return "-"
    institucion_estudiante.short_description = "Institución"

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
                        # Filtrar por la tabla intermedia EstudianteInstitucion
                        estudiante = Estudiante.objects.filter(
                            pk=estudiante_id,
                            instituciones_estudiante__institucion_id=institucion_id,
                            instituciones_estudiante__estado='activo'
                        ).first()
                        if not estudiante:
                            raise Estudiante.DoesNotExist("Estudiante no encontrado o no activo en esta institución")
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
                        # Obtener institución activa del estudiante
                        institucion_activa = estudiante.get_institucion_activa()
                        form.base_fields['institucion'].initial = institucion_activa
                        form.base_fields['nivel'].initial = siguiente_data['nivel']
                        form.base_fields['curso_lectivo'].initial = siguiente_data['curso_lectivo']
                        
                        # Manejar especialidad de manera especial para que funcione con Select2
                        if siguiente_data['especialidad']:
                            from config_institucional.models import EspecialidadCursoLectivo
                            
                            # Establecer el valor inicial
                            form.base_fields['especialidad'].initial = siguiente_data['especialidad']
                            
                            # Obtener todas las especialidades disponibles para la institución y nuevo curso
                            # PERO asegurar que la especialidad inicial esté incluida
                            especialidades_disponibles = EspecialidadCursoLectivo.objects.filter(
                                institucion=institucion_activa,
                                curso_lectivo=siguiente_data['curso_lectivo'],
                                activa=True
                            ).select_related('especialidad')
                            
                            # Verificar si la especialidad inicial está en las disponibles
                            if not especialidades_disponibles.filter(id=siguiente_data['especialidad'].id).exists():
                                # Si no está, agregar la especialidad actual al queryset usando union
                                from django.db.models import Q
                                especialidad_inicial_qs = EspecialidadCursoLectivo.objects.filter(
                                    id=siguiente_data['especialidad'].id
                                ).select_related('especialidad')
                                
                                # Combinar querysets
                                form.base_fields['especialidad'].queryset = especialidades_disponibles | especialidad_inicial_qs
                            else:
                                form.base_fields['especialidad'].queryset = especialidades_disponibles
                        
                        # Agregar mensaje informativo
                        form.base_fields['estudiante'].help_text = "Estudiante seleccionado automáticamente"
                        form.base_fields['nivel'].help_text = f"Nivel automático: {siguiente_data['nivel'].nombre}"
                        form.base_fields['curso_lectivo'].help_text = f"Curso automático: {siguiente_data['curso_lectivo'].nombre}"
                        if siguiente_data['especialidad']:
                            # siguiente_data['especialidad'] es un EspecialidadCursoLectivo, no una Especialidad
                            especialidad_nombre = str(siguiente_data['especialidad'])  # Usa el __str__ que ya maneja el acceso seguro
                            form.base_fields['especialidad'].help_text = f"Especialidad mantenida: {especialidad_nombre}"
                    else:
                        # Solo pre-llenar estudiante si no hay datos inteligentes
                        form.base_fields['estudiante'].initial = estudiante
                        institucion_activa = estudiante.get_institucion_activa()
                        form.base_fields['institucion'].initial = institucion_activa
                        form.base_fields['estudiante'].help_text = "Estudiante seleccionado. Complete manualmente los demás campos."
                else:
                    # Solo pre-llenar estudiante, proceso completamente manual
                    form.base_fields['estudiante'].initial = estudiante
                    institucion_activa = estudiante.get_institucion_activa()
                    form.base_fields['institucion'].initial = institucion_activa
                    form.base_fields['estudiante'].help_text = "Estudiante seleccionado. Complete manualmente nivel, curso lectivo y demás campos."
                        
            except (Estudiante.DoesNotExist, ValueError):
                pass
        
        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        # Campos bloqueados para todos los usuarios no superusuarios
        bloqueados = {"estudiante", "nivel"}
        if db_field.name in bloqueados and not request.user.is_superuser:
            field.widget.can_add_related = False
            field.widget.can_change_related = False
        
        # Bloquear sección y subgrupo según permisos específicos
        if db_field.name == "seccion":
            if not request.user.has_perm('catalogos.add_seccion'):
                field.widget.can_add_related = False
            if not request.user.has_perm('catalogos.change_seccion'):
                field.widget.can_change_related = False
        
        if db_field.name == "subgrupo":
            if not request.user.has_perm('catalogos.add_subgrupo'):
                field.widget.can_add_related = False
            if not request.user.has_perm('catalogos.change_subgrupo'):
                field.widget.can_change_related = False
        
        # Quitar límite artificial de 44 para no afectar filtros/selecciones
        # (DAL y filtros se encargan de paginar/cargar eficientemente)
        if db_field.name in ["seccion", "subgrupo"] and "queryset" not in kwargs:
            kwargs["queryset"] = db_field.related_model.objects.all()
        
        # DAL maneja el filtrado de especialidad, seccion y subgrupo automáticamente
        return field
    
    def save_model(self, request, obj, form, change):
        """Validar que el estudiante no esté dado de baja antes de crear/modificar matrícula"""
        # Verificar si el estudiante está dado de baja
        if not request.user.is_superuser:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id and obj.estudiante:
                relacion = EstudianteInstitucion.objects.filter(
                    estudiante=obj.estudiante,
                    institucion_id=institucion_id
                ).first()
                
                if relacion and relacion.estado != 'activo':
                    raise ValidationError(
                        f'No se puede crear o modificar una matrícula para un estudiante dado de baja. '
                        f'Estado actual: {relacion.get_estado_display()}. '
                        f'El estudiante debe estar activo en la institución.'
                    )
                elif not relacion:
                    raise ValidationError(
                        f'El estudiante no tiene una relación activa con su institución. '
                        f'No se puede crear una matrícula.'
                    )
        
        super().save_model(request, obj, form, change)

    def get_search_results(self, request, queryset, search_term):
        """Limitar resultados de búsqueda para evitar sobrecargar los selects"""
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        
        # Quitar recorte de resultados; el admin ya pagina y Jazzmin maneja UI
        
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


@admin.register(EstudianteInstitucion)
class EstudianteInstitucionAdmin(admin.ModelAdmin):
    """Admin para gestionar el historial institucional de estudiantes"""
    list_display = ('identificacion_estudiante', 'estudiante', 'institucion', 'estado_display', 'fecha_ingreso', 'fecha_salida', 'usuario_registro')
    list_filter = ('estado', 'institucion', 'fecha_ingreso', 'fecha_salida')
    search_fields = ('estudiante__identificacion', 'estudiante__primer_apellido', 'estudiante__nombres', 'institucion__nombre')
    readonly_fields = ('fecha_registro', 'usuario_registro')
    ordering = ('-fecha_ingreso', '-fecha_registro')
    actions = ['dar_baja_trasladado', 'dar_baja_retirado', 'dar_baja_graduado']
    
    def identificacion_estudiante(self, obj):
        """Mostrar identificación del estudiante"""
        if obj.estudiante:
            return obj.estudiante.identificacion
        return "-"
    identificacion_estudiante.short_description = "Identificación"
    identificacion_estudiante.admin_order_field = 'estudiante__identificacion'
    
    def estado_display(self, obj):
        """Mostrar estado con colores"""
        colores = {
            'activo': 'green',
            'trasladado': 'blue',
            'retirado': 'orange',
            'graduado': 'purple'
        }
        color = colores.get(obj.estado, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color,
            obj.get_estado_display()
        )
    estado_display.short_description = 'Estado'
    estado_display.admin_order_field = 'estado'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('estudiante', 'institucion', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_ingreso', 'fecha_salida')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'description': 'Historial de cambios y observaciones de esta relación institucional.'
        }),
        ('Auditoría', {
            'fields': ('fecha_registro', 'usuario_registro'),
            'classes': ('collapse',)
        }),
    )
    
    def changelist_view(self, request, extra_context=None):
        """Agregar contexto adicional a la vista de listado"""
        extra_context = extra_context or {}
        extra_context['title'] = 'Historial Institucional de Estudiantes'
        extra_context['subtitle'] = 'Registro completo de ingresos, salidas y traslados'
        return super().changelist_view(request, extra_context)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        # Usuarios normales solo ven relaciones de su institución
        institucion_id = getattr(request, 'institucion_activa_id', None)
        if institucion_id:
            return qs.filter(institucion_id=institucion_id)
        return qs.none()
    
    def save_model(self, request, obj, form, change):
        # Guardar el usuario que registró
        if not change:
            obj.usuario_registro = request.user
        super().save_model(request, obj, form, change)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "institucion" and not request.user.is_superuser:
            # Usuarios normales solo pueden seleccionar su institución
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                kwargs["queryset"] = Institucion.objects.filter(id=institucion_id)
                kwargs["initial"] = institucion_id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    @admin.action(description='Dar de baja por traslado')
    def dar_baja_trasladado(self, request, queryset):
        """Marca estudiantes como trasladados"""
        from django.utils import timezone
        # Solo actualizar los que están activos
        activos = queryset.filter(estado='activo')
        count = 0
        fecha_actual = timezone.now().date()
        
        for relacion in activos:
            relacion.estado = 'trasladado'
            relacion.fecha_salida = fecha_actual
            # Agregar observación con usuario y fecha
            observacion_nueva = f"Dado de baja por TRASLADO el {fecha_actual.strftime('%d/%m/%Y')} por {request.user.full_name() or request.user.email}"
            if relacion.observaciones:
                relacion.observaciones += f"\n{observacion_nueva}"
            else:
                relacion.observaciones = observacion_nueva
            relacion.save()
            count += 1
        
        self.message_user(
            request,
            f'{count} estudiante(s) marcado(s) como trasladado(s). Ahora pueden ser agregados a otra institución.',
            messages.SUCCESS
        )
    
    @admin.action(description='Dar de baja por retiro')
    def dar_baja_retirado(self, request, queryset):
        """Marca estudiantes como retirados"""
        from django.utils import timezone
        activos = queryset.filter(estado='activo')
        count = 0
        fecha_actual = timezone.now().date()
        
        for relacion in activos:
            relacion.estado = 'retirado'
            relacion.fecha_salida = fecha_actual
            # Agregar observación con usuario y fecha
            observacion_nueva = f"Dado de baja por RETIRO el {fecha_actual.strftime('%d/%m/%Y')} por {request.user.full_name() or request.user.email}"
            if relacion.observaciones:
                relacion.observaciones += f"\n{observacion_nueva}"
            else:
                relacion.observaciones = observacion_nueva
            relacion.save()
            count += 1
        
        self.message_user(
            request,
            f'{count} estudiante(s) marcado(s) como retirado(s).',
            messages.SUCCESS
        )
    
    @admin.action(description='Dar de baja por graduación')
    def dar_baja_graduado(self, request, queryset):
        """Marca estudiantes como graduados"""
        from django.utils import timezone
        activos = queryset.filter(estado='activo')
        count = 0
        fecha_actual = timezone.now().date()
        
        for relacion in activos:
            relacion.estado = 'graduado'
            relacion.fecha_salida = fecha_actual
            # Agregar observación con usuario y fecha
            observacion_nueva = f"Dado de baja por GRADUACIÓN el {fecha_actual.strftime('%d/%m/%Y')} por {request.user.full_name() or request.user.email}"
            if relacion.observaciones:
                relacion.observaciones += f"\n{observacion_nueva}"
            else:
                relacion.observaciones = observacion_nueva
            relacion.save()
            count += 1
        
        self.message_user(
            request,
            f'{count} estudiante(s) marcado(s) como graduado(s).',
            messages.SUCCESS
        )


@admin.register(AsignacionGrupos)
class AsignacionGruposAdmin(InstitucionScopedAdmin):
    """
    Admin para AsignacionGrupos con funcionalidad adicional para abrir la interfaz de asignación.
    """
    list_display = (
        'fecha_asignacion', 'curso_lectivo', 'nivel_nombre', 'total_estudiantes', 
        'secciones_utilizadas', 'subgrupos_utilizados', 'hermanos_agrupados', 'usuario_asignacion'
    )
    list_filter = ('curso_lectivo', 'nivel', 'fecha_asignacion', 'usuario_asignacion')
    search_fields = ('institucion__nombre', 'curso_lectivo__nombre', 'nivel__nombre', 'observaciones')
    ordering = ('-fecha_asignacion',)
    readonly_fields = (
        'fecha_asignacion', 'usuario_asignacion', 'total_estudiantes', 'total_mujeres', 
        'total_hombres', 'total_otros', 'secciones_utilizadas', 'subgrupos_utilizados', 
        'hermanos_agrupados', 'algoritmo_version'
    )
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('institucion', 'curso_lectivo', 'nivel', 'fecha_asignacion', 'usuario_asignacion')
        }),
        ('Estadísticas de Asignación', {
            'fields': (
                'total_estudiantes', 'total_mujeres', 'total_hombres', 'total_otros',
                'secciones_utilizadas', 'subgrupos_utilizadas', 'hermanos_agrupados'
            )
        }),
        ('Detalles Técnicos', {
            'fields': ('algoritmo_version', 'observaciones'),
            'classes': ('collapse',)
        })
    )
    
    def nivel_nombre(self, obj):
        """Mostrar nombre del nivel o 'Todos los niveles'"""
        return obj.nivel.nombre if obj.nivel else 'Todos los niveles'
    nivel_nombre.short_description = 'Nivel'
    nivel_nombre.admin_order_field = 'nivel__nombre'
    
    def has_add_permission(self, request):
        """Deshabilitar creación manual - solo vía interfaz de asignación"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Solo lectura para los registros"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Permitir eliminación solo a superusuarios"""
        return request.user.is_superuser
    
    def has_view_permission(self, request, obj=None):
        """Restringir vista al permiso custom de acceso."""
        if request.user.is_superuser:
            return True
        return request.user.has_perm('matricula.access_asignacion_grupos')

    def get_model_perms(self, request):
        """Ocultar el modelo del índice/admin si no tiene permiso de acceso."""
        if request.user.is_superuser:
            return super().get_model_perms(request)
        if not request.user.has_perm('matricula.access_asignacion_grupos'):
            return {}
        return super().get_model_perms(request)

    def changelist_view(self, request, extra_context=None):
        """Agregar botón para ir a la interfaz de asignación"""
        extra_context = extra_context or {}
        extra_context['asignacion_grupos_url'] = '/matricula/asignacion-grupos/'
        return super().changelist_view(request, extra_context)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Usuarios normales solo ven asignaciones de su institución
        institucion_id = getattr(request, 'institucion_activa_id', None)
        if institucion_id:
            return qs.filter(institucion_id=institucion_id)
        return qs.none()
