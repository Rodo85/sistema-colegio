from django.contrib import admin
from django import forms
from django.contrib.admin import RelatedOnlyFieldListFilter
from django.utils.html import format_html
from django.urls import reverse
from core.mixins import InstitucionScopedAdmin
from core.models import Institucion
from .models import NivelInstitucion, Profesor, Clase, PeriodoLectivo, EspecialidadCursoLectivo, SeccionCursoLectivo, SubgrupoCursoLectivo
from django.utils.safestring import mark_safe
from catalogos.models import SubArea, CursoLectivo, Seccion, Subgrupo

# NOTA: SubgrupoInline eliminado - ahora se maneja desde catalogos.admin

class ClaseInline(admin.TabularInline):
    model = Clase
    extra = 0
    fields = ("curso_lectivo", "subarea", "subgrupo", "profesor", "periodo")
    autocomplete_fields = ("curso_lectivo", "subarea", "subgrupo", "profesor")

@admin.register(Profesor)
class ProfesorAdmin(InstitucionScopedAdmin):
    list_display = ("usuario", "institucion", "identificacion")
    search_fields = (
        "usuario__first_name",
        "usuario__last_name",
        "usuario__second_last_name",
        "usuario__email",
        "identificacion",
    )
    autocomplete_fields = ("usuario",)

    # ---------- Permitir al superuser editar 'institucion' ----------
    def get_readonly_fields(self, request, obj=None):
        # Superuser: ningún campo de solo lectura
        if request.user.is_superuser:
            return ()
        # Director: 'institucion' se rellena automáticamente y no se puede cambiar
        return ("institucion",)

    # ---------- Filtrado del combo de institución ----------
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "institucion" and not request.user.is_superuser:
            # Para directores muestra solo su institución
            kwargs["queryset"] = Institucion.objects.filter(
                id=request.institucion_activa_id
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Clase)
class ClaseAdmin(InstitucionScopedAdmin):
    list_display = ("institucion", "curso_lectivo", "subarea", "subgrupo", "profesor", "periodo")
    list_filter  = (
        "institucion",
        "curso_lectivo",
        "periodo",
        "subarea__especialidad__modalidad__nombre",
        ("subgrupo", RelatedOnlyFieldListFilter),
    )
    autocomplete_fields = ("profesor", "subarea", "subgrupo", "curso_lectivo")

    # ---------- Filtrar combos y ajustar etiqueta de Subárea ----------
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ❶ Filtrado por institución (solo para directores)
        if not request.user.is_superuser:
            if db_field.name == "profesor":
                kwargs["queryset"] = Profesor.objects.filter(
                    institucion_id=request.institucion_activa_id
                )
            elif db_field.name == "subgrupo":
                # Por ahora mostrar todos los subgrupos, ya que nivel no tiene institución
                kwargs["queryset"] = Subgrupo.objects.all()
            elif db_field.name == "subarea":
                # Filtrar subáreas habilitadas para esta institución
                kwargs["queryset"] = SubArea.objects.filter(
                    subareainstitucion__institucion_id=request.institucion_activa_id,
                    subareainstitucion__activa=True
                ).distinct()
            elif db_field.name == "institucion":
                kwargs["queryset"] = Institucion.objects.filter(
                    id=request.institucion_activa_id
                )
            elif db_field.name == "curso_lectivo":
                # Solo mostrar cursos lectivos que tengan configuraciones activas para esta institución
                kwargs["queryset"] = CursoLectivo.objects.filter(
                    subgrupocursolectivo__institucion_id=request.institucion_activa_id,
                    subgrupocursolectivo__activa=True
                ).distinct()

        # ❷ Obtener el form-field original
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)

        # ❸ Personalizar SOLO la etiqueta del campo Subárea
        if db_field.name == "subarea":
            formfield.label_from_instance = lambda obj: obj.nombre

        return formfield

    def get_readonly_fields(self, request, obj=None):
        return () if request.user.is_superuser else ("institucion",)

# CursoLectivo ahora está en catalogos.admin

@admin.register(PeriodoLectivo)
class PeriodoLectivoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'curso_lectivo', 'institucion', 'fecha_inicio', 'fecha_fin')
    list_filter = ('curso_lectivo__anio', 'institucion')
    search_fields = ('nombre', 'curso_lectivo__nombre')
    ordering = ('curso_lectivo__anio', 'fecha_inicio')
    
    fieldsets = (
        ('Información General', {
            'fields': ('institucion', 'curso_lectivo', 'nombre')
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_fin')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Usuarios normales solo ven períodos de su institución
        return qs.filter(institucion=request.institucion_activa_id)

@admin.register(EspecialidadCursoLectivo)
class EspecialidadCursoLectivoAdmin(InstitucionScopedAdmin):
    list_display = ('id', 'institucion', 'curso_lectivo', 'especialidad', 'activa')
    list_filter = ('institucion', 'curso_lectivo__anio', 'especialidad__modalidad', 'activa')
    search_fields = ('institucion__nombre', 'curso_lectivo__nombre', 'especialidad__nombre')
    ordering = ('institucion__nombre', '-curso_lectivo__anio', 'especialidad__nombre')
    autocomplete_fields = ('institucion', 'curso_lectivo', 'especialidad')
    
    def get_fields(self, request, obj=None):
        """Personalizar campos según el tipo de usuario"""
        if request.user.is_superuser:
            return ('institucion', 'curso_lectivo', 'especialidad', 'activa')
        else:
            # Incluir 'institucion' para que el formulario la procese (se ocultará en get_form)
            return ('institucion', 'curso_lectivo', 'especialidad', 'activa')
    
    def get_readonly_fields(self, request, obj=None):
        # No marcar 'institucion' como solo lectura para permitir que el formulario lo envíe (aunque esté oculto)
        return () if request.user.is_superuser else ()
    
    def changelist_view(self, request, extra_context=None):
        """Personalizar la vista de lista para agregar botón de vista masiva"""
        extra_context = extra_context or {}
        
        # URL para la vista masiva
        vista_masiva_url = reverse('config_institucional:gestionar_especialidades_curso_lectivo')
        
        # Si el usuario no es superusuario, pre-seleccionar su institución
        if not request.user.is_superuser and hasattr(request, 'institucion_activa_id'):
            vista_masiva_url += f'?institucion={request.institucion_activa_id}'
        
        extra_context['vista_masiva_url'] = vista_masiva_url
        extra_context['vista_masiva_titulo'] = 'Gestión Masiva de Especialidades'
        
        return super().changelist_view(request, extra_context)
    
    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return (
                ('Información General', {
                    'fields': ('institucion', 'curso_lectivo', 'especialidad', 'activa')
                }),
            )
        # Usuarios normales: incluir institución (se ocultará por widget)
        return (
            ('Información General', {
                'fields': ('institucion', 'curso_lectivo', 'especialidad', 'activa')
            }),
        )

    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)
        institucion_id = getattr(request, 'institucion_activa_id', None)
        is_super = request.user.is_superuser

        class FormWithInst(Form):
            def __init__(self, *args, **kw):
                super().__init__(*args, **kw)
                if not is_super and institucion_id and 'institucion' in self.fields:
                    # ocultar y forzar valor
                    self.fields['institucion'].widget = forms.HiddenInput()
                    self.fields['institucion'].required = True
                    if self.is_bound:
                        data = self.data.copy()
                        key = self.add_prefix('institucion')
                        if not data.get(key):
                            data[key] = str(institucion_id)
                            self.data = data
                    else:
                        self.initial['institucion'] = institucion_id
                # Asegurar que el modelo tenga institucion antes de clean()
                if not is_super and institucion_id:
                    self.instance.institucion_id = institucion_id

            def clean(self):
                # Refuerzo: establecer institucion_id en la instancia antes de validaciones del modelo
                if not is_super and institucion_id:
                    self.instance.institucion_id = institucion_id
                return super().clean()

        return FormWithInst

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                obj.institucion_id = institucion_id
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'institucion' and not request.user.is_superuser:
            from core.models import Institucion
            inst_id = getattr(request, 'institucion_activa_id', None)
            if inst_id:
                kwargs['queryset'] = Institucion.objects.filter(id=inst_id)
                kwargs['initial'] = inst_id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def vista_masiva(self, obj):
        """Enlace a la vista masiva para gestionar especialidades."""
        if obj:
            url = reverse('config_institucional:gestionar_especialidades_curso_lectivo')
            return format_html(
                '<a href="{}?institucion={}&curso_lectivo={}" class="button" target="_blank">'
                '📋 Vista Masiva</a>',
                url, obj.institucion.id, obj.curso_lectivo.id
            )
        return "—"
    vista_masiva.short_description = "Vista Masiva"
    vista_masiva.allow_tags = True
    
    def get_readonly_fields(self, request, obj=None):
        # No marcar 'institucion' como solo lectura
        return () if request.user.is_superuser else ()


@admin.register(SeccionCursoLectivo)
class SeccionCursoLectivoAdmin(InstitucionScopedAdmin):
    """Admin para gestionar las secciones disponibles por curso lectivo."""
    
    list_display = ('institucion', 'curso_lectivo', 'seccion', 'activa')
    list_filter = ('institucion', 'curso_lectivo__anio', 'seccion__nivel', 'activa')
    search_fields = ('institucion__nombre', 'curso_lectivo__nombre', 'seccion__numero')
    ordering = ('institucion__nombre', '-curso_lectivo__anio', 'seccion__nivel__numero', 'seccion__numero')
    autocomplete_fields = ('institucion', 'curso_lectivo', 'seccion')
    
    def get_fields(self, request, obj=None):
        """Personalizar campos según el tipo de usuario"""
        if request.user.is_superuser:
            return ('institucion', 'curso_lectivo', 'seccion', 'activa')
        else:
            # Incluir 'institucion' para que el formulario la procese (se ocultará en get_form)
            return ('institucion', 'curso_lectivo', 'seccion', 'activa')
    
    # ⚡ ACCIONES MASIVAS PARA FACILITAR GESTIÓN
    actions = ['agregar_todas_secciones', 'copiar_del_año_anterior', 'activar_seleccionadas', 'desactivar_seleccionadas']
    
    def changelist_view(self, request, extra_context=None):
        """Personalizar la vista de lista para agregar botón de vista masiva"""
        extra_context = extra_context or {}
        
        # URL para la vista masiva
        vista_masiva_url = reverse('config_institucional:gestionar_secciones_curso_lectivo')
        
        # Si el usuario no es superusuario, pre-seleccionar su institución
        if not request.user.is_superuser and hasattr(request, 'institucion_activa_id'):
            vista_masiva_url += f'?institucion={request.institucion_activa_id}'
        
        extra_context['vista_masiva_url'] = vista_masiva_url
        extra_context['vista_masiva_titulo'] = 'Gestión Masiva de Secciones'
        
        return super().changelist_view(request, extra_context)
    
    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return (
                (None, {
                    'fields': ('institucion', 'curso_lectivo', 'seccion', 'activa')
                }),
            )
        return (
            (None, {
                'fields': ('institucion', 'curso_lectivo', 'seccion', 'activa')
            }),
        )

    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)
        institucion_id = getattr(request, 'institucion_activa_id', None)
        is_super = request.user.is_superuser

        class FormWithInst(Form):
            def __init__(self, *args, **kw):
                super().__init__(*args, **kw)
                if not is_super and institucion_id and 'institucion' in self.fields:
                    self.fields['institucion'].widget = forms.HiddenInput()
                    self.fields['institucion'].required = True
                    if self.is_bound:
                        data = self.data.copy()
                        key = self.add_prefix('institucion')
                        if not data.get(key):
                            data[key] = str(institucion_id)
                            self.data = data
                    else:
                        self.initial['institucion'] = institucion_id
                if not is_super and institucion_id:
                    self.instance.institucion_id = institucion_id

            def clean(self):
                if not is_super and institucion_id:
                    self.instance.institucion_id = institucion_id
                return super().clean()

        return FormWithInst

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                obj.institucion_id = institucion_id
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'institucion' and not request.user.is_superuser:
            from core.models import Institucion
            inst_id = getattr(request, 'institucion_activa_id', None)
            if inst_id:
                kwargs['queryset'] = Institucion.objects.filter(id=inst_id)
                kwargs['initial'] = inst_id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def vista_masiva(self, obj):
        """Enlace a la vista masiva para gestionar secciones."""
        if obj:
            url = reverse('config_institucional:gestionar_secciones_curso_lectivo')
            return format_html(
                '<a href="{}?institucion={}&curso_lectivo={}" class="button" target="_blank">'
                '📋 Vista Masiva</a>',
                url, obj.institucion.id, obj.curso_lectivo.id
            )
        return "—"
    vista_masiva.short_description = "Vista Masiva"
    vista_masiva.allow_tags = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(institucion=request.institucion_activa_id)
    
    def get_readonly_fields(self, request, obj=None):
        return () if request.user.is_superuser else ()
    
    def agregar_todas_secciones(self, request, queryset):
        """Agregar todas las secciones disponibles de la institución a un curso lectivo específico."""
        if not queryset.exists():
            self.message_user(request, "Seleccione al menos un registro.", level='warning')
            return
        
        # Obtener el primer curso lectivo seleccionado
        first_obj = queryset.first()
        curso_lectivo = first_obj.curso_lectivo
        institucion = first_obj.institucion
        
        # Obtener todas las secciones de la institución que no estén ya asignadas
        secciones_existentes = SeccionCursoLectivo.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_lectivo
        ).values_list('seccion_id', flat=True)
        
        # Obtener todas las secciones globales que no estén ya asignadas
        secciones_disponibles = Seccion.objects.all().exclude(id__in=secciones_existentes)
        
        # Crear las asignaciones
        creadas = 0
        for seccion in secciones_disponibles:
            SeccionCursoLectivo.objects.create(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
                seccion=seccion,
                activa=True
            )
            creadas += 1
        
        self.message_user(request, f"Se agregaron {creadas} secciones al curso {curso_lectivo.nombre}.")
    
    agregar_todas_secciones.short_description = "🚀 Agregar todas las secciones disponibles al curso lectivo"
    
    def copiar_del_año_anterior(self, request, queryset):
        """Copiar secciones del año anterior al año actual."""
        if not queryset.exists():
            self.message_user(request, "Seleccione al menos un registro.", level='warning')
            return
        
        first_obj = queryset.first()
        curso_actual = first_obj.curso_lectivo
        institucion = first_obj.institucion
        
        # Buscar el curso lectivo del año anterior
        año_anterior = curso_actual.anio - 1
        try:
            curso_anterior = CursoLectivo.objects.get(
                institucion=institucion,
                anio=año_anterior
            )
        except CursoLectivo.DoesNotExist:
            self.message_user(request, f"No se encontró curso lectivo para el año {año_anterior}.", level='error')
            return
        
        # Obtener secciones del año anterior
        secciones_año_anterior = SeccionCursoLectivo.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_anterior,
            activa=True
        )
        
        # Copiar al año actual (evitar duplicados)
        copiadas = 0
        for seccion_anterior in secciones_año_anterior:
            obj, created = SeccionCursoLectivo.objects.get_or_create(
                institucion=institucion,
                curso_lectivo=curso_actual,
                seccion=seccion_anterior.seccion,
                defaults={'activa': True}
            )
            if created:
                copiadas += 1
        
        self.message_user(request, f"Se copiaron {copiadas} secciones del año {año_anterior} al {curso_actual.anio}.")
    
    copiar_del_año_anterior.short_description = "📋 Copiar secciones del año anterior"
    
    def activar_seleccionadas(self, request, queryset):
        """Activar las secciones seleccionadas."""
        count = queryset.update(activa=True)
        self.message_user(request, f"Se activaron {count} secciones.")
    
    activar_seleccionadas.short_description = "✅ Activar secciones seleccionadas"
    
    def desactivar_seleccionadas(self, request, queryset):
        """Desactivar las secciones seleccionadas."""
        count = queryset.update(activa=False)
        self.message_user(request, f"Se desactivaron {count} secciones.")
    
    desactivar_seleccionadas.short_description = "❌ Desactivar secciones seleccionadas"


@admin.register(SubgrupoCursoLectivo)
class SubgrupoCursoLectivoAdmin(InstitucionScopedAdmin):
    """Admin para gestionar los subgrupos disponibles por curso lectivo."""
    
    list_display = ('institucion', 'curso_lectivo', 'subgrupo', 'especialidad_curso', 'activa')
    list_filter = ('institucion', 'curso_lectivo__anio', 'subgrupo__seccion__nivel', 'activa', 'especialidad_curso')
    search_fields = ('institucion__nombre', 'curso_lectivo__nombre', 'subgrupo__letra')
    ordering = ('institucion__nombre', '-curso_lectivo__anio', 'subgrupo__seccion__nivel__numero', 'subgrupo__letra')
    autocomplete_fields = ('institucion', 'curso_lectivo', 'subgrupo')  # especialidad_curso usa autocomplete personalizado

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'config_institucional/js/filter-especialidades-subgrupo.js',
        )
    
    def get_fields(self, request, obj=None):
        """Personalizar campos según el tipo de usuario"""
        if request.user.is_superuser:
            return ('institucion', 'curso_lectivo', 'subgrupo', 'especialidad_curso', 'activa')
        else:
            # Incluir 'institucion' para que el formulario la procese (se ocultará en get_form)
            return ('institucion', 'curso_lectivo', 'subgrupo', 'especialidad_curso', 'activa')

    def get_list_display(self, request):
        """Mostrar 'Subgrupo' primero; ocultar 'Institución' para usuarios no superusuarios"""
        base = ('subgrupo', 'curso_lectivo', 'especialidad_curso', 'activa')
        if request.user.is_superuser:
            return ('institucion',) + base
        return base

    def get_list_filter(self, request):
        """Ocultar filtro de institución para usuarios no superusuarios"""
        base = ('curso_lectivo__anio', 'subgrupo__seccion__nivel', 'activa', 'especialidad_curso')
        if request.user.is_superuser:
            return ('institucion',) + base
        return base

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Configurar autocomplete personalizado para especialidad_curso"""
        if db_field.name == 'especialidad_curso':
            from django import forms
            from dal import autocomplete
            
            # Configurar widget de autocomplete personalizado
            kwargs['widget'] = autocomplete.ModelSelect2(
                url='config_institucional:especialidad_curso_lectivo_autocomplete',
                forward=['institucion', 'curso_lectivo'],
                attrs={
                    'data-placeholder': 'Seleccionar especialidad...',
                    'data-minimum-input-length': 0,
                }
            )
            
        elif db_field.name == 'institucion' and not request.user.is_superuser:
            # Para usuarios no superusuarios, filtrar por su institución
            from core.models import Institucion
            inst_id = getattr(request, 'institucion_activa_id', None)
            if inst_id:
                kwargs['queryset'] = Institucion.objects.filter(id=inst_id)
                kwargs['initial'] = inst_id
                
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        """Personalizar formulario para usuarios no superusuarios"""
        Form = super().get_form(request, obj, **kwargs)
        institucion_id = getattr(request, 'institucion_activa_id', None)
        is_super = request.user.is_superuser

        class FormWithInst(Form):
            def __init__(self, *args, **kw):
                super().__init__(*args, **kw)
                if not is_super and institucion_id and 'institucion' in self.fields:
                    # ocultar y forzar valor
                    self.fields['institucion'].widget = forms.HiddenInput()
                    self.fields['institucion'].required = True
                    if self.is_bound:
                        data = self.data.copy()
                        key = self.add_prefix('institucion')
                        if not data.get(key):
                            data[key] = str(institucion_id)
                            self.data = data
                    else:
                        self.initial['institucion'] = institucion_id
                # Asegurar que el modelo tenga institucion antes de clean()
                if not is_super and institucion_id:
                    self.instance.institucion_id = institucion_id

            def clean(self):
                # Refuerzo: establecer institucion_id en la instancia antes de validaciones del modelo
                if not is_super and institucion_id:
                    self.instance.institucion_id = institucion_id
                return super().clean()

        return FormWithInst

    def save_model(self, request, obj, form, change):
        """Asegurar que se asigne la institución correcta para usuarios no superusuarios"""
        if not request.user.is_superuser:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                obj.institucion_id = institucion_id
        super().save_model(request, obj, form, change)
    
    # ⚡ ACCIONES MASIVAS PARA FACILITAR GESTIÓN
    actions = ['agregar_todos_subgrupos', 'copiar_del_año_anterior', 'activar_seleccionadas', 'desactivar_seleccionadas']
    
    def changelist_view(self, request, extra_context=None):
        """Personalizar la vista de lista para agregar botón de vista masiva"""
        extra_context = extra_context or {}
        
        # URL para la vista masiva
        vista_masiva_url = reverse('config_institucional:gestionar_subgrupos_curso_lectivo')
        
        # Si el usuario no es superusuario, pre-seleccionar su institución
        if not request.user.is_superuser and hasattr(request, 'institucion_activa_id'):
            vista_masiva_url += f'?institucion={request.institucion_activa_id}'
        
        extra_context['vista_masiva_url'] = vista_masiva_url
        extra_context['vista_masiva_titulo'] = 'Gestión Masiva de Subgrupos'
        
        return super().changelist_view(request, extra_context)
    
    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return (
                (None, {
                    'fields': ('institucion', 'curso_lectivo', 'subgrupo', 'especialidad_curso', 'activa')
                }),
            )
        return (
            (None, {
                'fields': ('institucion', 'curso_lectivo', 'subgrupo', 'especialidad_curso', 'activa')
            }),
        )

    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)
        institucion_id = getattr(request, 'institucion_activa_id', None)
        is_super = request.user.is_superuser

        class FormWithInst(Form):
            def __init__(self, *args, **kw):
                super().__init__(*args, **kw)
                if not is_super and institucion_id and 'institucion' in self.fields:
                    self.fields['institucion'].widget = forms.HiddenInput()
                    self.fields['institucion'].required = True
                    if self.is_bound:
                        data = self.data.copy()
                        key = self.add_prefix('institucion')
                        if not data.get(key):
                            data[key] = str(institucion_id)
                            self.data = data
                    else:
                        self.initial['institucion'] = institucion_id
                if not is_super and institucion_id:
                    self.instance.institucion_id = institucion_id

            def clean(self):
                if not is_super and institucion_id:
                    self.instance.institucion_id = institucion_id
                return super().clean()

        return FormWithInst
    
    def vista_masiva(self, obj):
        """Enlace a la vista masiva para gestionar subgrupos."""
        if obj:
            url = reverse('config_institucional:gestionar_subgrupos_curso_lectivo')
            return format_html(
                '<a href="{}?institucion={}&curso_lectivo={}" class="button" target="_blank">'
                '📋 Vista Masiva</a>',
                url, obj.institucion.id, obj.curso_lectivo.id
            )
        return "—"
    vista_masiva.short_description = "Vista Masiva"
    vista_masiva.allow_tags = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(institucion=request.institucion_activa_id)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if institucion_id:
                obj.institucion_id = institucion_id
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'institucion' and not request.user.is_superuser:
            from core.models import Institucion
            inst_id = getattr(request, 'institucion_activa_id', None)
            if inst_id:
                kwargs['queryset'] = Institucion.objects.filter(id=inst_id)
                kwargs['initial'] = inst_id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_readonly_fields(self, request, obj=None):
        return () if request.user.is_superuser else ()
    
    def agregar_todos_subgrupos(self, request, queryset):
        """Agregar todos los subgrupos disponibles de la institución a un curso lectivo específico."""
        if not queryset.exists():
            self.message_user(request, "Seleccione al menos un registro.", level='warning')
            return
        
        # Obtener el primer curso lectivo seleccionado
        first_obj = queryset.first()
        curso_lectivo = first_obj.curso_lectivo
        institucion = first_obj.institucion
        
        # Obtener todos los subgrupos de la institución que no estén ya asignados
        subgrupos_existentes = SubgrupoCursoLectivo.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_lectivo
        ).values_list('subgrupo_id', flat=True)
        
        # Obtener todos los subgrupos globales que no estén ya asignados
        subgrupos_disponibles = Subgrupo.objects.all().exclude(id__in=subgrupos_existentes)
        
        # Crear las asignaciones
        creados = 0
        for subgrupo in subgrupos_disponibles:
            SubgrupoCursoLectivo.objects.create(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
                subgrupo=subgrupo,
                activa=True
            )
            creados += 1
        
        self.message_user(request, f"Se agregaron {creados} subgrupos al curso {curso_lectivo.nombre}.")
    
    agregar_todos_subgrupos.short_description = "🚀 Agregar todos los subgrupos disponibles al curso lectivo"
    
    def copiar_del_año_anterior(self, request, queryset):
        """Copiar subgrupos del año anterior al año actual."""
        if not queryset.exists():
            self.message_user(request, "Seleccione al menos un registro.", level='warning')
            return
        
        first_obj = queryset.first()
        curso_actual = first_obj.curso_lectivo
        institucion = first_obj.institucion
        
        # Buscar el curso lectivo del año anterior
        año_anterior = curso_actual.anio - 1
        try:
            curso_anterior = CursoLectivo.objects.get(
                institucion=institucion,
                anio=año_anterior
            )
        except CursoLectivo.DoesNotExist:
            self.message_user(request, f"No se encontró curso lectivo para el año {año_anterior}.", level='error')
            return
        
        # Obtener subgrupos del año anterior
        subgrupos_año_anterior = SubgrupoCursoLectivo.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_anterior,
            activa=True
        )
        
        # Copiar al año actual (evitar duplicados)
        copiados = 0
        for subgrupo_anterior in subgrupos_año_anterior:
            obj, created = SubgrupoCursoLectivo.objects.get_or_create(
                institucion=institucion,
                curso_lectivo=curso_actual,
                subgrupo=subgrupo_anterior.subgrupo,
                defaults={'activa': True}
            )
            if created:
                copiados += 1
        
        self.message_user(request, f"Se copiaron {copiados} subgrupos del año {año_anterior} al {curso_actual.anio}.")
    
    copiar_del_año_anterior.short_description = "📋 Copiar subgrupos del año anterior"
    
    def activar_seleccionadas(self, request, queryset):
        """Activar los subgrupos seleccionados."""
        count = queryset.update(activa=True)
        self.message_user(request, f"Se activaron {count} subgrupos.")
    
    activar_seleccionadas.short_description = "✅ Activar subgrupos seleccionados"
    
    def desactivar_seleccionadas(self, request, queryset):
        """Desactivar los subgrupos seleccionados."""
        count = queryset.update(activa=False)
        self.message_user(request, f"Se desactivaron {count} subgrupos.")
    
    desactivar_seleccionadas.short_description = "❌ Desactivar subgrupos seleccionadas"



