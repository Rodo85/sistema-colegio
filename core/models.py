from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
import uuid
from django.conf import settings 
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
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email      = models.EmailField(unique=True)
    first_name = models.CharField("Nombre", max_length=50, blank=True)
    last_name  = models.CharField("1° Apellido", max_length=100, blank=True)
    second_last_name  = models.CharField("2° Apellido", max_length=50, blank=True)
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
    fecha_inicio  = models.DateField(auto_now_add=True)
    fecha_fin     = models.DateField()        # fecha de caducidad de licencia
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
