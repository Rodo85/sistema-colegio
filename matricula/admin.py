from django import forms
from django.contrib import admin

from core.mixins import InstitucionScopedAdmin
from .models import Estudiante, EncargadoEstudiante, PersonaContacto


# ─────────────────────────────  Formularios  ────────────────────────────
class EstudianteForm(forms.ModelForm):
    class Meta:
        model  = Estudiante
        fields = "__all__"
        widgets = {
            "identificacion": forms.TextInput(attrs={"autocomplete": "off"}),
            "provincia": forms.Select(),
            "canton":    forms.Select(),
            "distrito":  forms.Select(),
        }

    class Media:
        js = (
            "admin/js/jquery.init.js",
            "smart-selects/admin/js/chainedfk.js",
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
