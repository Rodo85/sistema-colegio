from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
import uuid
from datetime import date
from django.conf import settings 


def fecha_vencimiento_anual_default():
    hoy = date.today()
    return date(hoy.year, 12, 20)
# ───── 2.1  USER ────────────────────────────────────────────
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Correo requerido")
        email = self.normalize_email(email)
        user  = self.model(email=email, **extra)
        user.set_password(password)
        user.save()
        return user
    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)

class User(AbstractBaseUser, PermissionsMixin):
    ESTADO_PENDIENTE = "PENDIENTE"
    ESTADO_ACTIVA = "ACTIVA"
    ESTADO_RECHAZADA = "RECHAZADA"
    ESTADO_SOLICITUD_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_ACTIVA, "Activa"),
        (ESTADO_RECHAZADA, "Rechazada"),
    ]
    PAGO_PENDIENTE = "PENDIENTE"
    PAGO_AL_DIA = "AL_DIA"
    ESTADO_PAGO_CHOICES = [
        (PAGO_PENDIENTE, "Pago pendiente"),
        (PAGO_AL_DIA, "Al día"),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email      = models.EmailField(unique=True)
    first_name = models.CharField("Nombre", max_length=50, blank=True)
    last_name  = models.CharField("1° Apellido", max_length=100, blank=True)
    second_last_name  = models.CharField("2° Apellido", max_length=50, blank=True)
    estado_solicitud = models.CharField(
        "Estado de solicitud",
        max_length=20,
        choices=ESTADO_SOLICITUD_CHOICES,
        default=ESTADO_ACTIVA,
    )
    estado_pago = models.CharField(
        "Estado de pago",
        max_length=20,
        choices=ESTADO_PAGO_CHOICES,
        default=PAGO_AL_DIA,
    )
    fecha_limite_pago = models.DateField(
        "Fecha límite de pago",
        default=fecha_vencimiento_anual_default,
        help_text="Si llega esta fecha y no se renueva, el acceso se bloquea.",
    )
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    objects    = UserManager()
    
    def full_name(self):
        return f"{self.first_name} {self.last_name} {self.second_last_name}".strip()
    
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    USERNAME_FIELD = "email"
    def __str__(self):
        return self.email

    def dias_para_vencer_pago(self):
        if not self.fecha_limite_pago:
            return None
        return (self.fecha_limite_pago - date.today()).days

    def pago_vencido(self):
        if not self.fecha_limite_pago:
            return False
        return date.today() > self.fecha_limite_pago

    def save(self, *args, **kwargs):
        # Si cambia de "Pago pendiente" a "Al día", fijar vencimiento anual automáticamente.
        if self.pk:
            previo = type(self).objects.filter(pk=self.pk).values("estado_pago").first()
            if previo:
                if (
                    previo["estado_pago"] != self.PAGO_AL_DIA
                    and self.estado_pago == self.PAGO_AL_DIA
                ):
                    self.fecha_limite_pago = fecha_vencimiento_anual_default()
        super().save(*args, **kwargs)

# ───── 2.2  INSTITUCIÓN ────────────────────────────────────
class Institucion(models.Model):
    ACADEMICO = "A"
    TECNICO   = "T"
    TIPO_CHOICES = [
        (ACADEMICO, "Académico"),
        (TECNICO,   "Técnico"),
    ]
    nombre        = models.CharField(max_length=120, unique=True)
    correo        = models.EmailField(unique=True)
    telefono      = models.CharField(max_length=25, blank=True)
    direccion     = models.TextField(blank=True)
    tipo          = models.CharField(max_length=1, choices=TIPO_CHOICES)
    fecha_inicio  = models.DateField()
    fecha_fin     = models.DateField()        # fecha de caducidad de licencia
    logo          = models.ImageField("Logo institucional", upload_to="instituciones/logos/", null=True, blank=True)
    whatsapp_phone = models.CharField("WhatsApp emisor (E.164)", max_length=20, blank=True,
                                       help_text="Número remitente con prefijo país, ej. +5068XXXXXXX")
    whatsapp_token = models.CharField("Token API WhatsApp", max_length=255, blank=True)
    whatsapp_from_id = models.CharField("WhatsApp From (ID/phone)", max_length=50, blank=True,
                                        help_text="ID del teléfono o phone_number_id según proveedor")
    matricula_activa = models.BooleanField(
        "Matrícula activa",
        default=True,
        help_text="Determina si la institución trabaja con listas reales de matrícula.",
    )
    es_institucion_general = models.BooleanField(
        "Es institución general",
        default=False,
        help_text="Marca la institución genérica para docentes sin matrícula activa.",
    )
    max_asignaciones_general = models.PositiveSmallIntegerField(
        "Máximo de asignaciones (Institución General)",
        default=10,
        help_text="Límite por defecto aplicado a docentes de la Institución General.",
    )
    def save(self, *args, **kwargs):
        for campo in ("nombre", "correo", "telefono", "direccion"):
            valor = getattr(self, campo, None)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())
        # Si deseas forzar igualdad, descomenta:
        # if self.fecha_fin:
        #     self.fecha_inicio = self.fecha_fin
        super().save(*args, **kwargs)

    class Meta:
        ordering = ("nombre",)
        verbose_name = "Institución"          
        verbose_name_plural = "Instituciones"
    def __str__(self):
        return self.nombre
    @property
    def activa(self):
        from django.utils import timezone
        return self.fecha_fin >= timezone.now().date()

# ───── 2.3  MIEMBRO (usuario × institución × rol) ──────────
class Miembro(models.Model):
    ADMIN   = 1
    DOCENTE = 2
    STAFF   = 3
    ROL_CHOICES = [
        (ADMIN,   "Administrador"),
        (DOCENTE, "Docente"),
        (STAFF,   "Administrativo"),
    ]

    usuario     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membresias"
    )
    institucion = models.ForeignKey(
        "core.Institucion",
        on_delete=models.CASCADE,
        related_name="membresias"
    )
    rol         = models.PositiveSmallIntegerField(choices=ROL_CHOICES)

    class Meta:
        unique_together = ("usuario", "institucion")
        
    def __str__(self):
        return f"{self.usuario.email} – {self.get_rol_display()} @ {self.institucion}"


class SolicitudRegistro(models.Model):
    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"
    ESTADO_CHOICES = [
        (PENDIENTE, "Pendiente"),
        (APROBADA, "Aprobada"),
        (RECHAZADA, "Rechazada"),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitud_registro",
    )
    institucion_solicitada = models.ForeignKey(
        "core.Institucion",
        on_delete=models.PROTECT,
        related_name="solicitudes_registro",
        null=True,
        blank=True,
    )
    telefono_whatsapp = models.CharField(
        "WhatsApp de contacto",
        max_length=30,
        help_text="Número de contacto por WhatsApp para verificación.",
    )
    mensaje = models.TextField("Mensaje del solicitante", blank=True)
    comprobante_pago = models.ImageField(
        "Comprobante de pago",
        upload_to="solicitudes/comprobantes/",
        null=True,
        blank=True,
    )
    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=ESTADO_CHOICES,
        default=PENDIENTE,
    )
    motivo_revision = models.TextField(
        "Motivo de revisión/rechazo",
        blank=True,
    )
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_revisadas",
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-fecha_solicitud",)
        verbose_name = "Solicitud de registro"
        verbose_name_plural = "Solicitudes de registro"

    def __str__(self):
        return f"{self.usuario.email} - {self.estado}"
