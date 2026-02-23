from django.db import models
from django.utils import timezone


class AsistenciaSesion(models.Model):
    """
    Representa una pasada de lista (sesión) de un docente para una asignación,
    fecha y número de sesión determinados.
    Permite múltiples sesiones el mismo día (ej. lección 1, lección 2).
    """
    docente_asignacion = models.ForeignKey(
        "evaluaciones.DocenteAsignacion",
        on_delete=models.PROTECT,
        related_name="sesiones_asistencia",
        verbose_name="Asignación docente",
    )
    # Desnormalizado para facilitar reportes y filtros sin JOINs extras
    institucion = models.ForeignKey(
        "core.Institucion",
        on_delete=models.PROTECT,
        related_name="sesiones_asistencia",
        verbose_name="Institución",
    )
    curso_lectivo = models.ForeignKey(
        "catalogos.CursoLectivo",
        on_delete=models.PROTECT,
        related_name="sesiones_asistencia",
        verbose_name="Curso lectivo",
    )
    periodo = models.ForeignKey(
        "evaluaciones.Periodo",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="sesiones_asistencia",
        verbose_name="Período",
        help_text="Período lectivo al que pertenece la sesión (inferido por fecha si no se indica).",
    )
    fecha = models.DateField("Fecha", default=timezone.localdate, db_index=True)
    sesion_numero = models.PositiveSmallIntegerField(
        "N.° de sesión", default=1,
        help_text="Número de la sesión dentro del día (1, 2, 3…).",
    )
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sesiones_asistencia_creadas",
        verbose_name="Creado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asistencia_sesion"
        verbose_name = "Sesión de asistencia"
        verbose_name_plural = "Sesiones de asistencia"
        ordering = ("fecha", "sesion_numero")
        constraints = [
            models.UniqueConstraint(
                fields=["docente_asignacion", "periodo", "fecha", "sesion_numero"],
                name="uniq_sesion_asistencia",
            )
        ]
        indexes = [
            models.Index(fields=["docente_asignacion", "fecha"], name="asis_ses_asig_fecha_idx"),
            models.Index(fields=["periodo", "fecha"], name="asis_ses_periodo_fecha_idx"),
        ]
        permissions = [
            ("access_libro_docente", "Puede acceder al Libro del Docente"),
        ]

    def __str__(self):
        return f"Ses.{self.sesion_numero} – {self.fecha} – {self.docente_asignacion_id}"


class AsistenciaRegistro(models.Model):
    """
    Registro individual de asistencia: un estudiante en una sesión.
    """
    PRESENTE = "P"
    TARDIA = "T"
    AUSENTE_INJUSTIFICADA = "AI"
    AUSENTE_JUSTIFICADA = "AJ"
    ESTADO_CHOICES = [
        (PRESENTE, "Presente"),
        (TARDIA, "Tardía"),
        (AUSENTE_INJUSTIFICADA, "Ausente injustificada"),
        (AUSENTE_JUSTIFICADA, "Ausente justificada"),
    ]

    sesion = models.ForeignKey(
        AsistenciaSesion,
        on_delete=models.CASCADE,
        related_name="registros",
        verbose_name="Sesión",
    )
    estudiante = models.ForeignKey(
        "matricula.Estudiante",
        on_delete=models.PROTECT,
        related_name="registros_asistencia",
        verbose_name="Estudiante",
    )
    estado = models.CharField(
        "Estado",
        max_length=2,
        choices=ESTADO_CHOICES,
        default=AUSENTE_INJUSTIFICADA,
    )
    observacion = models.CharField("Observación", max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asistencia_registro"
        verbose_name = "Registro de asistencia"
        verbose_name_plural = "Registros de asistencia"
        constraints = [
            models.UniqueConstraint(
                fields=["sesion", "estudiante"],
                name="uniq_registro_por_sesion_estudiante",
            )
        ]
        indexes = [
            models.Index(fields=["sesion", "estudiante"], name="asis_reg_sesion_est_idx"),
        ]

    def __str__(self):
        return f"{self.estudiante} – {self.get_estado_display()} ({self.sesion.fecha})"
