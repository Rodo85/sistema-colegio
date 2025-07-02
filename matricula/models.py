from django.db import models
from smart_selects.db_fields import ChainedForeignKey

from core.models import Institucion
from catalogos.models import (
    TipoIdentificacion, Sexo, Nacionalidad,
    Provincia, Canton, Distrito,
    EstadoCivil, Parentesco, Escolaridad, Ocupacion,
)


# ─────────────────────────  PERSONA CONTACTO  ──────────────────────────
class PersonaContacto(models.Model):
    institucion       = models.ForeignKey(Institucion, on_delete=models.PROTECT)
    identificacion    = models.CharField("Identificación", max_length=20)
    primer_apellido   = models.CharField("1° Apellido", max_length=50)
    segundo_apellido  = models.CharField("2° Apellido", max_length=50, blank=True)
    nombres           = models.CharField("Nombre(s)",  max_length=100)
    celular_avisos    = models.CharField("Celular",    max_length=20, blank=True)
    correo            = models.CharField("Correo",     max_length=100, blank=True)
    lugar_trabajo     = models.CharField("Lugar de trabajo", max_length=100, blank=True)
    telefono_trabajo  = models.CharField("Teléfono trabajo", max_length=20, blank=True)

    estado_civil = models.ForeignKey(EstadoCivil,  on_delete=models.PROTECT)
    escolaridad  = models.ForeignKey(Escolaridad, on_delete=models.PROTECT)
    ocupacion    = models.ForeignKey(Ocupacion,   on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Persona de contacto"
        verbose_name_plural = "Personas de contacto"
        ordering = ("primer_apellido", "nombres")
        constraints = [
            models.UniqueConstraint(
                fields=["institucion", "identificacion"],
                name="unique_persona_contacto_por_institucion"
            )
        ]

    def save(self, *args, **kwargs):
        # normaliza a MAYÚSCULAS y sin espacios extra
        for campo in (
            "identificacion", "primer_apellido", "segundo_apellido",
            "nombres", "celular_avisos", "correo",
            "lugar_trabajo", "telefono_trabajo",
        ):
            valor = getattr(self, campo)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.primer_apellido} {self.nombres}"


# ──────────────────────────────  ESTUDIANTE  ───────────────────────────
class Estudiante(models.Model):
    PR = "PR"
    PN = "PN"
    TIPO_CHOICES = [
        (PR, "Plan regular"),
        (PN, "Plan nacional"),
    ]

    institucion         = models.ForeignKey(Institucion, on_delete=models.PROTECT)
    tipo_estudiante     = models.CharField("Tipo de estudiante", max_length=2,
                                           choices=TIPO_CHOICES, default=PR)
    tipo_identificacion = models.ForeignKey(TipoIdentificacion, on_delete=models.PROTECT)
    identificacion      = models.CharField("Identificación", max_length=20)

    primer_apellido   = models.CharField("1° Apellido", max_length=50)
    segundo_apellido  = models.CharField("2° Apellido", max_length=50, blank=True)
    nombres           = models.CharField("Nombre(s)",   max_length=100)

    fecha_nacimiento = models.DateField()
    celular         = models.CharField(max_length=20, blank=True)
    telefono_casa   = models.CharField(max_length=20, blank=True)

    sexo         = models.ForeignKey(Sexo,         on_delete=models.PROTECT)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)

    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT)

    canton = ChainedForeignKey(
        Canton,                               # modelo hijo
        chained_field="provincia",            # FK en ESTE modelo
        chained_model_field="provincia",      # FK en el modelo hijo
        show_all=False,
        auto_choose=False,
        sort=True,
        blank=True, null=True,
        on_delete=models.PROTECT,
    )

    distrito = ChainedForeignKey(
        Distrito,
        chained_field="canton",
        chained_model_field="canton",
        show_all=False,
        auto_choose=False,
        sort=True,
        blank=True, null=True,
        on_delete=models.PROTECT,
    )

    direccion_exacta = models.TextField(blank=True)

    contactos = models.ManyToManyField(
        PersonaContacto,
        through="EncargadoEstudiante",
        related_name="estudiantes",
    )

    class Meta:
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"
        ordering = ("primer_apellido", "nombres")
        constraints = [
            models.UniqueConstraint(
                fields=["institucion", "identificacion"],
                name="unique_estudiante_por_institucion"
            )
        ]

    def save(self, *args, **kwargs):
        for campo in (
            "identificacion", "primer_apellido", "segundo_apellido",
            "nombres", "celular", "telefono_casa", "direccion_exacta",
        ):
            valor = getattr(self, campo)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.primer_apellido} {self.nombres}"


# ────────────────────────  TABLA INTERMEDIA  ───────────────────────────
class EncargadoEstudiante(models.Model):
    estudiante       = models.ForeignKey(Estudiante,      on_delete=models.CASCADE)
    persona_contacto = models.ForeignKey(PersonaContacto, on_delete=models.CASCADE)
    parentesco       = models.ForeignKey(Parentesco,      on_delete=models.PROTECT)
    convivencia      = models.BooleanField("Convive con el estudiante", default=False)

    class Meta:
        verbose_name = "Encargado de estudiante"
        verbose_name_plural = "Encargados de estudiantes"
        unique_together = ("estudiante", "persona_contacto", "parentesco")

    def __str__(self):
        return f"{self.persona_contacto} – {self.estudiante} ({self.parentesco})"
