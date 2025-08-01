from django.db import models
from smart_selects.db_fields import ChainedForeignKey

from core.models import Institucion
from catalogos.models import (
    TipoIdentificacion, Sexo, Nacionalidad,
    Provincia, Canton, Distrito,
    EstadoCivil, Parentesco, Escolaridad, Ocupacion, Adecuacion,
    Nivel, Especialidad,
)
from config_institucional.models import Seccion, Subgrupo, PeriodoLectivo


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
        for campo in (
            "identificacion", "primer_apellido", "segundo_apellido",
            "nombres", "celular_avisos", "lugar_trabajo", "telefono_trabajo",
        ):
            valor = getattr(self, campo, None)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())
        # Correos electrónicos en minúscula
        if self.correo:
            self.correo = self.correo.strip().lower()
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

    canton = models.ForeignKey(
    Canton,
    on_delete=models.PROTECT,
    blank=True, null=True
    )

    distrito = models.ForeignKey(
        Distrito,
        on_delete=models.PROTECT,
        blank=True, null=True
    )

    direccion_exacta = models.TextField(blank=True)
    
    foto = models.ImageField(
        "Foto del estudiante",
        upload_to='estudiantes/fotos/%Y/%m/',
        blank=True,
        null=True,
        help_text="Foto del estudiante (formato: JPG, PNG. Máximo 2MB)"
    )

    contactos = models.ManyToManyField(
        PersonaContacto,
        through="EncargadoEstudiante",
        related_name="estudiantes",
    )

    correo = models.EmailField("Correo electrónico MEP", max_length=100, null=True, blank=True)
    ed_religiosa = models.BooleanField("Recibe Ed. Religiosa", default=False)
    recibe_afectividad_sexualidad = models.BooleanField("Recibe Afectividad y Sexualidad", default=False)
    adecuacion = models.ForeignKey(Adecuacion, on_delete=models.PROTECT, blank=True, null=True)
    rige_poliza = models.DateField("Rige Póliza", blank=True, null=True)
    vence_poliza = models.DateField("Vence Póliza", blank=True, null=True)
    presenta_enfermedad = models.BooleanField("Presenta alguna enfermedad", default=False)
    detalle_enfermedad = models.CharField("Nombre de la(s) enfermedad(es)", max_length=255, blank=True)
    autoriza_derecho_imagen = models.BooleanField("Autoriza derecho de imagen", default=False)
    numero_poliza = models.CharField("Número de póliza", max_length=50, blank=True)
    fecha_matricula = models.DateField("Fecha registro", null=True, blank=True)

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
            "nombres", "celular", "telefono_casa", "direccion_exacta", "numero_poliza"
        ):
            valor = getattr(self, campo)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())
        # Correos electrónicos en minúscula
        if self.correo:
            self.correo = self.correo.strip().lower()
        # Generar correo automáticamente
        if self.identificacion:
            self.correo = f"{self.identificacion}@est.mep.go.cr"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.primer_apellido} {self.nombres}"


# ────────────────────────  TABLA INTERMEDIA  ───────────────────────────
class EncargadoEstudiante(models.Model):
    estudiante       = models.ForeignKey(Estudiante,      on_delete=models.CASCADE)
    persona_contacto = models.ForeignKey(PersonaContacto, on_delete=models.CASCADE)
    parentesco       = models.ForeignKey(Parentesco,      on_delete=models.PROTECT)
    convivencia      = models.BooleanField("Convive con el estudiante", blank=True)

    class Meta:
        verbose_name = "Encargado de estudiante"
        verbose_name_plural = "Encargados de estudiantes"
        unique_together = ("estudiante", "persona_contacto", "parentesco")

    def __str__(self):
        return f"{self.persona_contacto} – {self.estudiante} ({self.parentesco})"

    def save(self, *args, **kwargs):
        # Normalizar campos de texto si los hay
        for campo in ("convivencia",):
            valor = getattr(self, campo, None)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())
        super().save(*args, **kwargs)

# Eliminar modelos duplicados de Nivel, Seccion, Subgrupo, Periodo
# Mantener solo el modelo de MatriculaAcademica, referenciando los modelos correctos

class MatriculaAcademica(models.Model):
    ACTIVO = 'activo'
    RETIRADO = 'retirado'
    PROMOVIDO = 'promovido'
    REPITENTE = 'repitente'
    ESTADO_CHOICES = [
        (ACTIVO, 'Activo'),
        (RETIRADO, 'Retirado'),
        (PROMOVIDO, 'Promovido'),
        (REPITENTE, 'Repitente'),
    ]
    estudiante = models.ForeignKey('Estudiante', on_delete=models.CASCADE, related_name='matriculas_academicas')
    nivel = models.ForeignKey(Nivel, on_delete=models.PROTECT)
    seccion = models.ForeignKey(Seccion, on_delete=models.PROTECT)
    subgrupo = models.ForeignKey(Subgrupo, on_delete=models.PROTECT, null=True, blank=True)
    periodo = models.ForeignKey(PeriodoLectivo, on_delete=models.PROTECT)
    fecha_asignacion = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ACTIVO)
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT, null=True, blank=True)
    class Meta:
        verbose_name = "Matrícula académica"
        verbose_name_plural = "Matrículas académicas"
        unique_together = ("estudiante", "nivel", "seccion", "subgrupo", "periodo")
    def __str__(self):
        return f"{self.estudiante} - {self.nivel} {self.seccion} {self.subgrupo or ''} ({self.periodo})"

    def save(self, *args, **kwargs):
        # Normalizar campos de texto si los hay
        for campo in ("estado",):
            valor = getattr(self, campo, None)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())
        super().save(*args, **kwargs)
