from django.db import models
from django.utils import timezone


class BecaComedor(models.Model):
    institucion = models.ForeignKey(
        "core.Institucion",
        on_delete=models.PROTECT,
        related_name="becas_comedor",
    )
    curso_lectivo = models.ForeignKey(
        "catalogos.CursoLectivo",
        on_delete=models.PROTECT,
        related_name="becas_comedor",
    )
    estudiante = models.ForeignKey(
        "matricula.Estudiante",
        on_delete=models.PROTECT,
        related_name="becas_comedor",
    )
    activa = models.BooleanField(default=True)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    usuario_asignacion = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="becas_comedor_asignadas",
    )
    usuario_actualizacion = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="becas_comedor_actualizadas",
    )

    class Meta:
        verbose_name = "Beca de comedor"
        verbose_name_plural = "Becas de comedor"
        ordering = ("estudiante__primer_apellido", "estudiante__nombres")
        constraints = [
            models.UniqueConstraint(
                fields=["institucion", "curso_lectivo", "estudiante"],
                name="uniq_beca_comedor_por_estudiante_anio_institucion",
            )
        ]
        permissions = [
            ("access_registro_beca_comedor", "Puede gestionar becas de comedor"),
            ("access_almuerzo_comedor", "Puede registrar almuerzo en comedor"),
            ("access_reportes_comedor", "Puede acceder a reportes de comedor"),
        ]

    def __str__(self):
        estado = "Activa" if self.activa else "Inactiva"
        return f"{self.estudiante} - {self.curso_lectivo} ({estado})"


class RegistroAlmuerzo(models.Model):
    institucion = models.ForeignKey(
        "core.Institucion",
        on_delete=models.PROTECT,
        related_name="registros_almuerzo",
    )
    curso_lectivo = models.ForeignKey(
        "catalogos.CursoLectivo",
        on_delete=models.PROTECT,
        related_name="registros_almuerzo",
    )
    estudiante = models.ForeignKey(
        "matricula.Estudiante",
        on_delete=models.PROTECT,
        related_name="registros_almuerzo",
    )
    fecha = models.DateField(default=timezone.localdate, db_index=True)
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    usuario_registro = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="almuerzos_registrados",
    )
    observacion = models.CharField(max_length=250, blank=True)

    class Meta:
        verbose_name = "Registro de almuerzo"
        verbose_name_plural = "Registros de almuerzo"
        ordering = ("-fecha_hora",)
        constraints = [
            models.UniqueConstraint(
                fields=["institucion", "curso_lectivo", "estudiante", "fecha"],
                name="uniq_almuerzo_diario_por_estudiante",
            )
        ]
        indexes = [
            models.Index(fields=["institucion", "curso_lectivo", "fecha"]),
        ]

    def __str__(self):
        return f"{self.estudiante} - {self.fecha_hora:%d/%m/%Y %H:%M}"

