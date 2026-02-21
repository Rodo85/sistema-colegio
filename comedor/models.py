import uuid

from django.db import models
from django.utils import timezone


class ConfiguracionComedor(models.Model):
    institucion = models.OneToOneField(
        "core.Institucion",
        on_delete=models.CASCADE,
        related_name="configuracion_comedor",
        verbose_name="Institución",
    )
    intervalo_minutos = models.PositiveIntegerField(
        default=1200,
        verbose_name="Intervalo mínimo entre registros (minutos)",
        help_text=(
            "Tiempo mínimo en minutos que debe pasar entre dos registros del mismo estudiante. "
            "Ejemplo: 120 = puede registrar desayuno y almuerzo. 1200 = prácticamente una vez al día."
        ),
    )

    class Meta:
        verbose_name = "Configuración de comedor"
        verbose_name_plural = "Configuraciones de comedor"

    def __str__(self):
        return f"{self.institucion.nombre} – {self.intervalo_minutos} min"


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
            ("access_tiquetes_comedor", "Puede gestionar tiquetes de comedor"),
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

    class Meta:
        verbose_name = "Registro de almuerzo"
        verbose_name_plural = "Registros de almuerzo"
        ordering = ("-fecha_hora",)
        indexes = [
            models.Index(fields=["institucion", "curso_lectivo", "fecha"]),
            models.Index(fields=["institucion", "curso_lectivo", "estudiante", "fecha_hora"]),
        ]

    def __str__(self):
        return f"{self.estudiante} - {self.fecha_hora:%d/%m/%Y %H:%M}"


class TiqueteComedor(models.Model):
    ALUMNO_TIQ = "ALUMNO_TIQ"
    PROFESOR = "PROFESOR"
    TIPO_CHOICES = [
        (ALUMNO_TIQ, "Alumno con tiquete"),
        (PROFESOR, "Profesor"),
    ]

    codigo = models.CharField("Código", max_length=20, unique=True, editable=False)
    tipo = models.CharField("Tipo", max_length=15, choices=TIPO_CHOICES)
    monto = models.DecimalField("Monto (₡)", max_digits=10, decimal_places=2, default=0)
    activo = models.BooleanField("Activo", default=True)
    institucion = models.ForeignKey(
        "core.Institucion",
        on_delete=models.PROTECT,
        related_name="tiquetes_comedor",
        verbose_name="Institución",
    )
    created_at = models.DateTimeField("Fecha de creación", auto_now_add=True)
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tiquetes_comedor_creados",
        verbose_name="Creado por",
    )

    class Meta:
        verbose_name = "Tiquete de comedor"
        verbose_name_plural = "Tiquetes de comedor"
        ordering = ("tipo", "codigo")

    def __str__(self):
        estado = "✓" if self.activo else "✗"
        return f"[{estado}] {self.get_tipo_display()} – {self.codigo}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            prefijo = "PRF" if self.tipo == self.PROFESOR else "TIQ"
            for _ in range(20):
                candidato = f"{prefijo}-{uuid.uuid4().hex[:8].upper()}"
                if not TiqueteComedor.objects.filter(codigo=candidato).exists():
                    self.codigo = candidato
                    break
        super().save(*args, **kwargs)


class RegistroAlmuerzoTiquete(models.Model):
    institucion = models.ForeignKey(
        "core.Institucion",
        on_delete=models.PROTECT,
        related_name="registros_almuerzo_tiquete",
        verbose_name="Institución",
    )
    curso_lectivo = models.ForeignKey(
        "catalogos.CursoLectivo",
        on_delete=models.PROTECT,
        related_name="registros_almuerzo_tiquete",
        verbose_name="Curso lectivo",
    )
    tiquete = models.ForeignKey(
        TiqueteComedor,
        on_delete=models.PROTECT,
        related_name="registros_almuerzo",
        verbose_name="Tiquete",
    )
    fecha = models.DateField(default=timezone.localdate, db_index=True)
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Registro de almuerzo (tiquete)"
        verbose_name_plural = "Registros de almuerzo (tiquetes)"
        ordering = ("-fecha_hora",)
        indexes = [
            models.Index(fields=["institucion", "curso_lectivo", "fecha"]),
            models.Index(fields=["tiquete", "fecha_hora"]),
        ]

    def __str__(self):
        return f"{self.tiquete.get_tipo_display()} ({self.tiquete.codigo}) – {self.fecha_hora:%d/%m/%Y %H:%M}"

