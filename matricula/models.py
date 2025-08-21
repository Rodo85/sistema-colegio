from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from smart_selects.db_fields import ChainedForeignKey

from core.models import Institucion, User
from catalogos.models import (
    TipoIdentificacion, Sexo, Nacionalidad,
    Provincia, Canton, Distrito,
    EstadoCivil, Parentesco, Escolaridad, Ocupacion, Adecuacion,
    Nivel, Especialidad, CursoLectivo,
)
from config_institucional.models import Seccion, Subgrupo, PeriodoLectivo


# ─────────────────────────  PERSONA CONTACTO  ──────────────────────────
class PersonaContacto(models.Model):
    institucion       = models.ForeignKey(Institucion, on_delete=models.PROTECT)
    identificacion    = models.CharField("Identificación", max_length=20)
    primer_apellido   = models.CharField("1° Apellido", max_length=50)
    segundo_apellido  = models.CharField("2° Apellido", max_length=50, blank=True)
    nombres           = models.CharField("Nombre(s)",  max_length=100)
    celular_avisos    = models.CharField("Celular",    max_length=20)
    correo            = models.CharField("Correo",     max_length=100)
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
    segundo_apellido  = models.CharField("2° Apellido", max_length=50)
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

    direccion_exacta = models.TextField()
    
    foto = models.ImageField("Foto", upload_to='estudiantes/fotos/%Y/%m/', blank=True, null=True)
    correo = models.CharField("Correo electrónico", max_length=100, blank=True, null=True)
    ed_religiosa = models.BooleanField("Recibe Ed. Religiosa", default=False)
    rige_poliza = models.DateField("Rige Póliza", blank=True, null=True)
    vence_poliza = models.DateField("Vence Póliza", blank=True, null=True)
    presenta_enfermedad = models.BooleanField("Presenta alguna enfermedad", default=False)
    detalle_enfermedad = models.CharField("Nombre de la(s) enfermedad(es)", max_length=255, blank=True)
    autoriza_derecho_imagen = models.BooleanField("Autoriza derecho de imagen", default=False)
    numero_poliza = models.CharField("Número de póliza", max_length=50, blank=True)
    adecuacion = models.ForeignKey(Adecuacion, on_delete=models.PROTECT, blank=True, null=True)
    medicamento_consume = models.TextField("Medicamentos que consume", blank=True, null=True)

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
    principal        = models.BooleanField("Es encargado principal", default=False)

    class Meta:
        verbose_name = "Encargado de estudiante"
        verbose_name_plural = "Encargados de estudiantes"
        unique_together = ("estudiante", "persona_contacto", "parentesco")
        constraints = [
            # Un solo encargado principal por estudiante
            models.UniqueConstraint(
                fields=["estudiante"],
                condition=Q(principal=True),
                name="unique_principal_por_estudiante",
            ),
        ]

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
    seccion = models.ForeignKey(Seccion, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Sección")
    subgrupo = models.ForeignKey(Subgrupo, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Subgrupo")
    curso_lectivo = models.ForeignKey('catalogos.CursoLectivo', on_delete=models.PROTECT, verbose_name="Curso Lectivo")
    fecha_asignacion = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ACTIVO, null=True, blank=True)
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT, null=True, blank=True)
    
    class Meta:
        verbose_name = "Matrícula académica"
        verbose_name_plural = "Matrículas académicas"
        unique_together = ("estudiante", "nivel", "seccion", "subgrupo", "curso_lectivo")
    
    def __str__(self):
        return f"{self.estudiante} - {self.nivel} {self.seccion or ''} {self.subgrupo or ''} ({self.curso_lectivo})"

    def save(self, *args, **kwargs):
        # No alterar "estado": debe coincidir con las keys de choices ('activo', 'retirado', ...)
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar especialidad para décimo, undécimo y duodécimo
        if self.nivel and self.nivel.nombre in ['Décimo', 'Undécimo', 'Duodécimo']:
            if not self.especialidad:
                raise ValidationError("La especialidad es obligatoria para décimo, undécimo y duodécimo.")
        
        # Solo validar si el estudiante ya está guardado (tiene pk)
        if self.estado == 'activo' and self.curso_lectivo and self.estudiante and getattr(self.estudiante, 'pk', None):
            existe = MatriculaAcademica.objects.filter(
                estudiante=self.estudiante,
                curso_lectivo=self.curso_lectivo,
                estado='activo'
            ).exclude(pk=self.pk).exists()
            if existe:
                raise ValidationError("Ya existe una matrícula activa para este curso lectivo.")
        super().clean()

    @classmethod
    def get_siguiente_matricula_data(cls, estudiante, curso_lectivo_actual):
        """
        Obtiene los datos para la siguiente matrícula de un estudiante
        """
        from catalogos.models import Nivel, CursoLectivo
        
        # Buscar matrícula activa en el curso lectivo actual del estudiante
        matricula_actual = cls.objects.filter(
            estudiante=estudiante,
            curso_lectivo=curso_lectivo_actual,
            estado__iexact='activo'
        ).first()
        
        if not matricula_actual:
            return None  # No hay matrícula activa, proceso manual
        
        # Obtener siguiente nivel
        nivel_actual = matricula_actual.nivel
        try:
            siguiente_nivel = Nivel.objects.get(numero=nivel_actual.numero + 1)
        except Nivel.DoesNotExist:
            return None  # No hay siguiente nivel disponible
        
        # Obtener siguiente curso lectivo (ahora es global)
        try:
            siguiente_curso = CursoLectivo.objects.get(anio=curso_lectivo_actual.anio + 1)
        except CursoLectivo.DoesNotExist:
            return None  # No hay siguiente curso lectivo disponible
        
        # Preparar datos para siguiente matrícula
        siguiente_data = {
            'nivel': siguiente_nivel,
            'curso_lectivo': siguiente_curso,
            'especialidad': None,
        }
        
        # Para niveles 10→11 y 11→12, mantener la especialidad
        if nivel_actual.numero in [10, 11]:
            siguiente_data['especialidad'] = matricula_actual.especialidad
        
        return siguiente_data

    @classmethod
    def get_especialidades_disponibles(cls, institucion, curso_lectivo):
        """
        Obtiene las especialidades disponibles para una institución y curso lectivo específicos.
        Solo retorna las especialidades que han sido configuradas como activas.
        """
        from config_institucional.models import EspecialidadCursoLectivo
        
        especialidades_configuradas = EspecialidadCursoLectivo.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_lectivo,
            activa=True
        ).values_list('especialidad_id', flat=True)
        
        return Especialidad.objects.filter(id__in=especialidades_configuradas)

class PlantillaImpresionMatricula(models.Model):
    titulo = models.CharField("Título principal", max_length=200)
    logo_mep = models.ImageField("Logo MEP", upload_to="plantillas/logos_mep/", null=False, blank=False)
    encabezado = models.TextField("Encabezado superior", help_text="Puedes usar variables como {{ institucion.nombre }}")
    pie_pagina = models.TextField("Pie de página", help_text="Puedes usar variables como {{ institucion.nombre }}")

    def save(self, *args, **kwargs):
        if PlantillaImpresionMatricula.objects.exists() and not self.pk:
            raise Exception("Solo puede existir una plantilla global de impresión de matrícula.")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Plantilla global de impresión de matrícula"
        verbose_name_plural = "Plantilla global de impresión de matrícula"
