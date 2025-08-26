from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

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
    id = models.AutoField(primary_key=True)
    institucion       = models.ForeignKey(Institucion, on_delete=models.PROTECT)
    tipo_identificacion = models.ForeignKey(TipoIdentificacion, on_delete=models.PROTECT, verbose_name="Tipo de identificación")
    identificacion    = models.CharField("Identificación", max_length=20)
    primer_apellido   = models.CharField("1° Apellido", max_length=50)

    # ← ahora permite NULL
    segundo_apellido  = models.CharField("2° Apellido", max_length=50, blank=True, null=True)

    nombres           = models.CharField("Nombre(s)",  max_length=100)

    # ← ahora permiten NULL
    celular_avisos    = models.CharField("Celular", max_length=20, blank=True, null=True)
    correo            = models.CharField("Correo", max_length=100, blank=True, null=True)
    lugar_trabajo     = models.CharField("Lugar de trabajo", max_length=100, blank=True, null=True)
    telefono_trabajo  = models.CharField("Teléfono trabajo", max_length=20, blank=True, null=True)

    # ← ahora permiten NULL
    estado_civil = models.ForeignKey(EstadoCivil, on_delete=models.PROTECT, blank=True, null=True)
    escolaridad  = models.ForeignKey(Escolaridad, on_delete=models.PROTECT, blank=True, null=True)
    ocupacion    = models.ForeignKey(Ocupacion,   on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        verbose_name = "Persona de contacto"
        verbose_name_plural = "Personas de contacto"
        ordering = ("primer_apellido", "nombres")
        constraints = [
            models.UniqueConstraint(
                fields=["institucion", "identificacion"],
                name="unique_persona_contacto_por_institucion",
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar que si es cédula, tenga exactamente 9 dígitos
        if self.tipo_identificacion and self.identificacion:
            tipo_nombre = self.tipo_identificacion.nombre.upper()
            if 'CÉDULA' in tipo_nombre or 'CEDULA' in tipo_nombre:
                if not self.identificacion.isdigit() or len(self.identificacion) != 9:
                    raise ValidationError({
                        'identificacion': 'La cédula debe tener exactamente 9 dígitos numéricos.'
                    })

    def save(self, *args, **kwargs):
        # Normaliza strings: recorta y a MAYÚSCULA (correo se maneja aparte)
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

    # ======== SOLO estos campos quedan NO NULOS ========
    institucion         = models.ForeignKey(Institucion, on_delete=models.PROTECT)                    # NOT NULL
    tipo_estudiante     = models.CharField("Tipo de estudiante", max_length=2, choices=TIPO_CHOICES, default=PR)  # NOT NULL
    tipo_identificacion = models.ForeignKey(TipoIdentificacion, on_delete=models.PROTECT)             # NOT NULL
    identificacion      = models.CharField("Identificación", max_length=20)                           # NOT NULL
    primer_apellido     = models.CharField("1° Apellido", max_length=50)                              # NOT NULL
    segundo_apellido    = models.CharField("2° Apellido", max_length=50)                              # NOT NULL
    nombres             = models.CharField("Nombre(s)", max_length=100)                               # NOT NULL
    fecha_nacimiento    = models.DateField()                                                          # NOT NULL
    sexo                = models.ForeignKey(Sexo, on_delete=models.PROTECT)                           # NOT NULL
    nacionalidad        = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)                   # NOT NULL
    correo              = models.CharField("Correo electrónico", max_length=100)                      # NOT NULL

    # ======== TODOS los demás pueden ser NULOS ========
    celular           = models.CharField(max_length=20, blank=True, null=True)
    telefono_casa     = models.CharField(max_length=20, blank=True, null=True)

    provincia         = models.ForeignKey(Provincia, on_delete=models.PROTECT, blank=True, null=True)
    canton            = models.ForeignKey(Canton, on_delete=models.PROTECT, blank=True, null=True)
    distrito          = models.ForeignKey(Distrito, on_delete=models.PROTECT, blank=True, null=True)

    direccion_exacta  = models.TextField(blank=True, null=True)

    foto              = models.ImageField("Foto", upload_to='estudiantes/fotos/%Y/%m/', blank=True, null=True)
    ed_religiosa      = models.BooleanField("Recibe Ed. Religiosa", blank=True, null=True)
    rige_poliza       = models.DateField("Rige Póliza", blank=True, null=True)
    vence_poliza      = models.DateField("Vence Póliza", blank=True, null=True)
    presenta_enfermedad = models.BooleanField("Presenta alguna enfermedad", blank=True, null=True)
    detalle_enfermedad  = models.CharField("Nombre de la(s) enfermedad(es)", max_length=255, blank=True, null=True)
    autoriza_derecho_imagen = models.BooleanField("Autoriza derecho de imagen", blank=True, null=True)
    numero_poliza     = models.CharField("Número de póliza", max_length=50, blank=True, null=True)
    adecuacion        = models.ForeignKey(Adecuacion, on_delete=models.PROTECT, blank=True, null=True)
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
        # Normaliza strings: recorta y MAYÚSCULAS (correo se maneja aparte)
        for campo in (
            "identificacion", "primer_apellido", "segundo_apellido",
            "nombres", "celular", "telefono_casa", "direccion_exacta", "numero_poliza"
        ):
            valor = getattr(self, campo, None)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip().upper())

        # Correos electrónicos en minúscula y obligatorio (no nulo).
        # Si hay identificación, construye el institucional.
        if self.identificacion:
            self.correo = f"{self.identificacion.strip()}@est.mep.go.cr".lower()
        elif isinstance(self.correo, str):
            self.correo = self.correo.strip().lower()

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
    estudiante = models.ForeignKey('Estudiante', on_delete=models.PROTECT, related_name='matriculas_academicas')
    nivel = models.ForeignKey(Nivel, on_delete=models.PROTECT)
    seccion = models.ForeignKey(Seccion, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Sección")
    subgrupo = models.ForeignKey(Subgrupo, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Subgrupo")
    curso_lectivo = models.ForeignKey('catalogos.CursoLectivo', on_delete=models.PROTECT, verbose_name="Curso Lectivo")
    fecha_asignacion = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default=ACTIVO)
    especialidad = models.ForeignKey('config_institucional.EspecialidadCursoLectivo', on_delete=models.PROTECT, null=True, blank=True, verbose_name="Especialidad del curso lectivo")
    
    class Meta:
        verbose_name = "Matrícula académica"
        verbose_name_plural = "Matrículas académicas"
        # Evita dos matrículas ACTIVAS en el mismo año
        constraints = [
            models.UniqueConstraint(
                fields=['estudiante', 'curso_lectivo'],
                condition=Q(estado='activo'),
                name='uniq_matricula_activa_por_anio',
            ),
        ]
    
    def __str__(self):
        return f"{self.estudiante} - {self.nivel} {self.seccion or ''} {self.subgrupo or ''} ({self.curso_lectivo})"

    @property
    def institucion(self):
        """Obtiene la institución a través del estudiante"""
        if hasattr(self, 'estudiante') and self.estudiante:
            return getattr(self.estudiante, 'institucion', None)
        return None

    def save(self, *args, **kwargs):
        # Validar que el estudiante tenga institución antes de guardar
        if hasattr(self, 'estudiante') and self.estudiante:
            if not hasattr(self.estudiante, 'institucion') or not self.estudiante.institucion:
                from django.core.exceptions import ValidationError
                raise ValidationError("El estudiante debe tener una institución asignada.")
        
        # No alterar "estado": debe coincidir con las keys of choices ('activo', 'retirado', ...)
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # 1) Especialidad obligatoria solo para décimo (10)
        if self.nivel and getattr(self.nivel, 'numero', None) == 10:
            if not self.especialidad:
                raise ValidationError("La especialidad es obligatoria para décimo (10°).")
        
        # 2) Para niveles 11 y 12, verificar si hay especialidad previa de décimo
        elif self.nivel and getattr(self.nivel, 'numero', None) in [11, 12]:
            if not self.especialidad:
                # Buscar si hay matrícula de décimo con especialidad
                matricula_10 = MatriculaAcademica.objects.filter(
                    estudiante=self.estudiante,
                    nivel__numero=10,
                    estado='activo'
                ).first()
                if not matricula_10 or not matricula_10.especialidad:
                    raise ValidationError("Para 11° y 12° debe seleccionar una especialidad si no existe una asignada en décimo.")

        # 3) Coherencia ECL ↔ curso lectivo (y, si aplica, institución del estudiante)
        if self.especialidad:
            if self.especialidad.curso_lectivo_id != self.curso_lectivo_id:
                raise ValidationError("La especialidad seleccionada no corresponde a este curso lectivo.")

            # Si Estudiante tiene FK a Institución, valide también:
            if hasattr(self.estudiante, 'institucion_id'):
                if self.especialidad.institucion_id != self.estudiante.institucion_id:
                    raise ValidationError("La especialidad no pertenece a la institución del estudiante.")

        # 4) Salvaguarda adicional (evita dos activas por año aunque cambie sección/subgrupo)
        if (self.estado == 'activo' and self.curso_lectivo_id and getattr(self.estudiante, 'pk', None)):
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
        
        # Verificar que la especialidad siga siendo válida para el siguiente curso lectivo
        if siguiente_data['especialidad']:
            try:
                from config_institucional.models import EspecialidadCursoLectivo
                especialidad_valida = EspecialidadCursoLectivo.objects.filter(
                    institucion=estudiante.institucion,
                    curso_lectivo=siguiente_curso,
                    especialidad=siguiente_data['especialidad'].especialidad,
                    activa=True
                ).first()
                
                if not especialidad_valida:
                    # La especialidad no está disponible en el siguiente curso, no asignarla
                    siguiente_data['especialidad'] = None
            except Exception:
                # Si hay error, no asignar especialidad
                siguiente_data['especialidad'] = None
        
        return siguiente_data

    @classmethod
    def get_especialidades_disponibles(cls, institucion, curso_lectivo):
        """
        Obtiene las especialidades disponibles para una institución y curso lectivo específicos.
        Solo retorna las especialidades que han sido configuradas como activas.
        """
        from config_institucional.models import EspecialidadCursoLectivo
        return (
            EspecialidadCursoLectivo.objects
            .filter(institucion=institucion, curso_lectivo=curso_lectivo, activa=True)
            .select_related('especialidad', 'especialidad__modalidad')
            .order_by('especialidad__nombre')
        )

class PlantillaImpresionMatricula(models.Model):
    institucion = models.ForeignKey(
        "core.Institucion", 
        on_delete=models.CASCADE, 
        verbose_name="Institución",
        help_text="Institución a la que pertenece esta plantilla"
    )
    titulo = models.CharField("Título principal", max_length=200)
    logo_mep = models.ImageField("Logo MEP", upload_to="plantillas/logos_mep/", null=False, blank=False)
    encabezado = models.TextField("Encabezado superior", help_text="Puedes usar variables como {{ institucion.nombre }}")
    pie_pagina = models.TextField("Pie de página", help_text="Puedes usar variables como {{ institucion.nombre }}")

    def save(self, *args, **kwargs):
        # Verificar que no exista otra plantilla para la misma institución
        if PlantillaImpresionMatricula.objects.filter(institucion=self.institucion).exists() and not self.pk:
            raise Exception(f"Ya existe una plantilla para la institución {self.institucion.nombre}.")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Plantilla de impresión de matrícula"
        verbose_name_plural = "Plantillas de impresión de matrícula"
        unique_together = ['institucion']

    def __str__(self):
        return f"Plantilla - {self.institucion.nombre}"
