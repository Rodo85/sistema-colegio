from django import forms
from django.contrib import admin
from django.utils.html import format_html

from core.mixins import InstitucionScopedAdmin
from .models import Estudiante, EncargadoEstudiante, PersonaContacto, MatriculaAcademica
from .widgets import ImagePreviewWidget
from catalogos.models import Provincia, Canton, Distrito
from .forms import MatriculaAcademicaForm

# ─────────────────────────────  Formularios  ────────────────────────────
class EstudianteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'provincia' in self.fields and not self.instance.pk:
            primera_provincia = Provincia.objects.first()
            if primera_provincia:
                self.fields['provincia'].initial = primera_provincia.id

    class Meta:
        model = Estudiante
        fields = "__all__"
        widgets = {
            'provincia': forms.Select(attrs={'id': 'id_provincia'}),
            'canton': forms.Select(attrs={'id': 'id_canton'}),
            'distrito': forms.Select(attrs={'id': 'id_distrito'}),
            'identificacion': forms.TextInput(attrs={'autocomplete': 'off'}),
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
    class Meta:
        model  = PersonaContacto
        fields = "__all__"
        widgets = {
            "identificacion": forms.TextInput(attrs={"autocomplete": "off"}),
        }
    class Media:
        js = (
            'admin/js/jquery.init.js',
        )

# ────────────────────────────  Inline  ──────────────────────────────────
class EncargadoInline(admin.TabularInline):
    model = EncargadoEstudiante
    extra = 0

class MatriculaAcademicaInline(admin.StackedInline):  # Cambiado a StackedInline para vista vertical
    model = MatriculaAcademica
    form = MatriculaAcademicaForm
    extra = 0
    fields = ('periodo', 'nivel', 'seccion', 'subgrupo', 'estado', 'especialidad')
    # Permitir histórico, no forzar matrícula inmediata
    # Validar que no haya doble matrícula activa en el mismo periodo
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        original_save_new = formset.save_new
        def save_new_with_validation(form, commit=True):
            instance = original_save_new(form, commit=False)
            # Solo validar si la matrícula es activa y tiene periodo y estudiante
            if instance.estado == 'activo' and instance.periodo and instance.estudiante:
                existe = MatriculaAcademica.objects.filter(
                    estudiante=instance.estudiante,
                    periodo=instance.periodo,
                    estado='activo'
                ).exclude(pk=instance.pk).exists()
                if existe:
                    from django.core.exceptions import ValidationError
                    raise ValidationError("Ya existe una matrícula activa para este periodo.")
            if commit:
                instance.save()
            return instance
        formset.save_new = save_new_with_validation
        return formset

# ────────────────────────  Estudiante admin  ───────────────────────────
@admin.register(Estudiante)
class EstudianteAdmin(InstitucionScopedAdmin):
    form    = EstudianteForm
    inlines = [EncargadoInline, MatriculaAcademicaInline]
    fields = None  # Fuerza el uso de fieldsets

    # Mejorar búsqueda: usar ^ para búsquedas desde el inicio
    search_fields = ("^identificacion", "^primer_apellido", "^nombres")

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
                    'foto',  # <-- Agregado aquí
                ),
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
                    'ed_religiosa', 'recibe_afectividad_sexualidad', 'adecuacion',
                    'numero_poliza', 'rige_poliza', 'vence_poliza', 'fecha_matricula',
                    'presenta_enfermedad', 'detalle_enfermedad',
                    'autoriza_derecho_imagen',
                ),
            })
        )
        return fieldsets

    # Quitar foto de la lista
    list_display  = ("identificacion", "primer_apellido", "segundo_apellido", "nombres", "tipo_estudiante")
    # Solo búsqueda por identificación
    search_fields = ("identificacion",)
    # Filtros igual
    list_filter   = ("institucion", "tipo_estudiante", "sexo", "nacionalidad")
    list_per_page = 25
    ordering = ("primer_apellido", "nombres")

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        # Limitar resultados del autocomplete a 20
        return queryset[:20], use_distinct

    def foto_miniatura(self, obj):
        if obj.foto:
            return format_html(
                '<img src="{}" alt="Foto" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 1px solid #ddd;" />',
                obj.foto.url
            )
        return format_html(
            '<div style="width: 40px; height: 40px; border-radius: 50%; background-color: #f0f0f0; display: flex; align-items: center; justify-content: center; border: 1px solid #ddd; color: #999; font-size: 12px;">Sin foto</div>'
        )
    foto_miniatura.short_description = "Foto"

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
                'identificacion',
                'primer_apellido', 'segundo_apellido', 'nombres',
                'estado_civil', 'escolaridad', 'ocupacion',
                'celular_avisos', 'correo', 'lugar_trabajo', 'telefono_trabajo',
            ),
        }),
    )

    list_display  = ("primer_apellido", "nombres", "identificacion", "institucion", "celular_avisos")
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

@admin.register(MatriculaAcademica)
class MatriculaAcademicaAdmin(admin.ModelAdmin):
    # Solo usar autocomplete_fields para evitar combobox con miles de opciones
    autocomplete_fields = ("estudiante", "nivel", "seccion", "subgrupo")
    list_display = ("estudiante", "nivel", "seccion", "subgrupo", "periodo", "estado", "fecha_asignacion")
    search_fields = ("estudiante__identificacion", "estudiante__primer_apellido", "estudiante__nombres")
    list_filter = ("nivel", "seccion", "subgrupo", "periodo", "estado")
