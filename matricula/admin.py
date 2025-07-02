from django import forms
from django.contrib import admin

from core.mixins import InstitucionScopedAdmin
from .models import Estudiante, EncargadoEstudiante, PersonaContacto
from catalogos.models import Provincia

# ─────────────────────────────  Formularios  ────────────────────────────
class EstudianteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Establecer la primera provincia como valor por defecto
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
        }

    class Media:
        js = (
            'admin/js/jquery.init.js',
            'matricula/js/dependent-dropdowns.js',
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

    fields = [
        "institucion", "tipo_estudiante",
        "tipo_identificacion", "identificacion",
        "primer_apellido", "segundo_apellido", "nombres",
        "fecha_nacimiento", "celular", "telefono_casa",
        "sexo", "nacionalidad",
        "provincia", "canton", "distrito",
        "direccion_exacta",
    ]

    list_display  = ("primer_apellido", "segundo_apellido", "nombres", "institucion")
    search_fields = ("primer_apellido", "segundo_apellido", "nombres", "identificacion")
    list_filter   = ("institucion", "tipo_estudiante")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        bloqueados = {
            "institucion", "tipo_identificacion", "sexo", "nacionalidad",
            "provincia", "canton", "distrito",
        }
        if db_field.name in bloqueados and not request.user.is_superuser:
            field.widget.can_add_related = False
            field.widget.can_change_related = False
        return field


# ───────────────────────  Persona-Contacto admin  ───────────────────────
@admin.register(PersonaContacto)
class PersonaContactoAdmin(InstitucionScopedAdmin):
    form = PersonaContactoForm

    list_display  = ("primer_apellido", "nombres", "identificacion", "institucion")
    search_fields = ("primer_apellido", "segundo_apellido", "nombres", "identificacion", "correo")
    list_filter   = ("estado_civil", "ocupacion")
