from django import forms
from django.contrib import admin
from django.utils.html import format_html

from core.mixins import InstitucionScopedAdmin
from .models import Estudiante, EncargadoEstudiante, PersonaContacto
from .widgets import ImagePreviewWidget
from catalogos.models import Provincia, Canton, Distrito

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
        }

    class Media:
        js = (
            'admin/js/jquery.init.js',
            "matricula/js/dependent-dropdowns.js"
        )

class PersonaContactoForm(forms.ModelForm):
    class Meta:
        model  = PersonaContacto
        fields = "__all__"
        widgets = {
            "identificacion": forms.TextInput(attrs={"autocomplete": "off"}),
        }

# ────────────────────────────  Inline  ──────────────────────────────────
class EncargadoInline(admin.TabularInline):
    model = EncargadoEstudiante
    extra = 0

# ────────────────────────  Estudiante admin  ───────────────────────────
@admin.register(Estudiante)
class EstudianteAdmin(InstitucionScopedAdmin):
    form    = EstudianteForm
    inlines = [EncargadoInline]
    fields = None  # Fuerza el uso de fieldsets

    fieldsets = (
        ('Información Institucional', {
            'fields': ('institucion', 'tipo_estudiante'),
            'classes': ('collapse',)
        }),
        ('Identificación', {
            'fields': ('tipo_identificacion', 'identificacion'),
        }),
        ('Datos Personales', {
            'fields': (
                'primer_apellido', 'segundo_apellido', 'nombres',
                'fecha_nacimiento', 'sexo', 'nacionalidad', 'foto'
            ),
        }),
        ('Información de Contacto', {
            'fields': ('celular', 'telefono_casa'),
        }),
        ('Dirección', {
            'fields': ('provincia', 'canton', 'distrito', 'direccion_exacta'),
            'description': 'Seleccione la provincia para cargar los cantones disponibles, luego seleccione el cantón para cargar los distritos.'
        }),
    )
    #mostrar foto, identificacion, primer apellido, segundo apellido, nombres, tipo de estudiante en el panel de administracion
    list_display  = ("foto_miniatura", "identificacion", "primer_apellido", "segundo_apellido", "nombres", "tipo_estudiante")
    search_fields = ("primer_apellido", "segundo_apellido", "nombres", "identificacion")
    list_filter   = ("institucion", "tipo_estudiante", "sexo", "nacionalidad")
    list_per_page = 25
    ordering = ("primer_apellido", "nombres")

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
        ('Identificación', {
            'fields': ('identificacion',),
        }),
        ('Datos Personales', {
            'fields': (
                'primer_apellido', 'segundo_apellido', 'nombres',
                'estado_civil', 'escolaridad', 'ocupacion'
            ),
        }),
        ('Información de Contacto', {
            'fields': ('celular_avisos', 'correo', 'lugar_trabajo', 'telefono_trabajo'),
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
