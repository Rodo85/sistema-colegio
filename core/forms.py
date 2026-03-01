from django import forms
from datetime import date
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from core.models import Institucion


User = get_user_model()


class PendingAwareAdminAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        estado = getattr(user, "estado_solicitud", User.ESTADO_ACTIVA)
        if estado == User.ESTADO_PENDIENTE:
            raise ValidationError(
                "Tu solicitud está pendiente de aprobación. Te notificaremos cuando sea activada.",
                code="pendiente",
            )
        if estado == User.ESTADO_RECHAZADA:
            raise ValidationError(
                "Tu solicitud fue rechazada. Contacta al administrador si crees que es un error.",
                code="rechazada",
            )
        if not user.is_superuser:
            fecha_limite = getattr(user, "fecha_limite_pago", None)
            if fecha_limite and date.today() > fecha_limite:
                raise ValidationError(
                    "Tu período de prueba o acceso expiró. Contacta al administrador para renovar tu pago.",
                    code="pago_vencido",
                )


class RegistroUsuarioForm(UserCreationForm):
    OPCION_LISTA = "LISTA"
    OPCION_GENERAL = "GENERAL"
    COLEGIO_OPCIONES = [
        (OPCION_LISTA, "Mi colegio aparece en la lista"),
        (OPCION_GENERAL, "Mi colegio no tiene matrícula activa / no aparece"),
    ]

    colegio_opcion = forms.ChoiceField(
        choices=COLEGIO_OPCIONES,
        widget=forms.RadioSelect,
        initial=OPCION_LISTA,
        label="Selección de colegio",
    )
    institucion = forms.ModelChoiceField(
        queryset=Institucion.objects.none(),
        required=False,
        label="Colegio",
    )
    mensaje = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Mensaje (opcional)",
    )
    telefono_whatsapp = forms.CharField(
        required=True,
        max_length=30,
        label="Número de WhatsApp",
        help_text="Ejemplo: +50686724880",
    )
    comprobante_pago = forms.ImageField(
        required=False,
        label="Comprobante de pago",
    )

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "second_last_name",
            "email",
        )
        labels = {
            "first_name": "Nombre",
            "last_name": "Primer apellido",
            "second_last_name": "Segundo apellido",
            "email": "Correo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["institucion"].queryset = Institucion.objects.filter(
            matricula_activa=True,
            es_institucion_general=False,
        ).order_by("nombre")
        self.fields["password1"].label = "Contraseña"
        self.fields["password2"].label = "Confirmar contraseña"
        self.fields["password1"].help_text = "Mínimo 8 caracteres, con letras y al menos un número."
        for name, field in self.fields.items():
            css = "form-control"
            if name == "colegio_opcion":
                css = ""
            if field.widget.__class__.__name__ == "Textarea":
                field.widget.attrs.setdefault("class", "form-control")
            elif css:
                field.widget.attrs.setdefault("class", css)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email.endswith("@mep.go.cr"):
            raise forms.ValidationError("El correo debe ser institucional y terminar en @mep.go.cr.")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email

    def clean(self):
        cleaned = super().clean()
        opcion = cleaned.get("colegio_opcion")
        institucion = cleaned.get("institucion")
        if opcion == self.OPCION_LISTA and not institucion:
            self.add_error("institucion", "Debes seleccionar un colegio de la lista.")
        return cleaned

    def clean_password1(self):
        password = self.cleaned_data.get("password1") or ""
        errores = []
        if len(password) < 8:
            errores.append("Debe tener al menos 8 caracteres.")
        if not any(ch.isdigit() for ch in password):
            errores.append("Debe incluir al menos un número.")
        if not any(ch.isalpha() for ch in password):
            errores.append("Debe incluir al menos una letra.")
        if errores:
            raise forms.ValidationError(" ".join(errores))
        return password
