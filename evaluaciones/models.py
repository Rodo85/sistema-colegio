from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


# ═══════════════════════════════════════════════════════════════════════════
#  CATÁLOGOS GLOBALES DE EVALUACIÓN
# ═══════════════════════════════════════════════════════════════════════════

class ComponenteEval(models.Model):
    """
    Catálogo global de componentes de evaluación.
    Ejemplos: COTIDIANO, TAREAS, PRUEBAS, ASISTENCIA, PROYECTO, PORTAFOLIO, DEMOSTRACION.
    Solo el superusuario puede modificar este catálogo.
    """
    codigo = models.CharField("Código", max_length=30, unique=True)
    nombre = models.CharField("Nombre", max_length=100)
    descripcion = models.TextField("Descripción", blank=True)
    activo = models.BooleanField("Activo", default=True)

    class Meta:
        db_table = "eval_component"
        verbose_name = "Componente de evaluación"
        verbose_name_plural = "Componentes de evaluación"
        ordering = ("nombre",)
        permissions = [
            ("access_eval_components", "Puede gestionar componentes de evaluación"),
        ]

    def __str__(self):
        return f"{self.codigo} – {self.nombre}"

    def save(self, *args, **kwargs):
        if self.codigo:
            self.codigo = self.codigo.strip().upper()
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
        super().save(*args, **kwargs)


class EsquemaEval(models.Model):
    """
    Plantilla/esquema de evaluación reutilizable.
    Puede estar ligado a una modalidad/especialidad (técnica) o ser académico.
    Cuando locked=True: no se pueden editar componentes y se exige suma=100%.
    """
    ACADEMICO = "ACADEMICO"
    TECNICO = "TECNICO"
    TIPO_CHOICES = [
        (ACADEMICO, "Académico"),
        (TECNICO, "Técnico"),
    ]

    nombre = models.CharField("Nombre", max_length=150)
    tipo = models.CharField("Tipo", max_length=10, choices=TIPO_CHOICES)
    modalidad = models.ForeignKey(
        "catalogos.Modalidad",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Modalidad",
        related_name="esquemas_eval",
    )
    especialidad = models.ForeignKey(
        "catalogos.Especialidad",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Especialidad",
        related_name="esquemas_eval",
    )
    vigente_desde = models.DateField("Vigente desde", null=True, blank=True)
    vigente_hasta = models.DateField("Vigente hasta", null=True, blank=True)
    locked = models.BooleanField(
        "Bloqueado",
        default=False,
        help_text=(
            "Si está bloqueado no se pueden editar sus componentes "
            "y la suma de porcentajes debe ser exactamente 100%."
        ),
    )
    activo = models.BooleanField("Activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "eval_scheme"
        verbose_name = "Esquema de evaluación"
        verbose_name_plural = "Esquemas de evaluación"
        ordering = ("tipo", "nombre")
        permissions = [
            ("access_eval_schemes", "Puede gestionar esquemas de evaluación"),
        ]

    def __str__(self):
        lock = " [BLOQUEADO]" if self.locked else ""
        return f"[{self.get_tipo_display()}] {self.nombre}{lock}"

    def get_total_porcentaje(self):
        return self.componentes_esquema.aggregate(
            total=models.Sum("porcentaje")
        )["total"] or Decimal("0")

    def clean(self):
        if self.vigente_desde and self.vigente_hasta:
            if self.vigente_hasta < self.vigente_desde:
                raise ValidationError(
                    "La fecha 'vigente hasta' no puede ser anterior a 'vigente desde'."
                )
        if self.locked and self.pk:
            total = self.get_total_porcentaje()
            if total != Decimal("100"):
                raise ValidationError(
                    f"No se puede bloquear: la suma de porcentajes es {total}% (debe ser 100%)."
                )
        super().clean()

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
        super().save(*args, **kwargs)


class EsquemaEvalComponente(models.Model):
    """
    Detalle del esquema: porcentaje asignado a cada componente.
    Los porcentajes deben estar entre 0 y 100.
    La suma total por esquema debe ser 100 (validado en Python y por trigger PG si locked).
    """
    esquema = models.ForeignKey(
        EsquemaEval,
        on_delete=models.CASCADE,
        related_name="componentes_esquema",
        verbose_name="Esquema",
    )
    componente = models.ForeignKey(
        ComponenteEval,
        on_delete=models.PROTECT,
        related_name="esquemas",
        verbose_name="Componente",
    )
    porcentaje = models.DecimalField(
        "Porcentaje (%)",
        max_digits=5,
        decimal_places=2,
        help_text="Valor entre 0.00 y 100.00.",
    )
    reglas_json = models.JSONField(
        "Reglas adicionales",
        default=dict,
        blank=True,
        help_text='Ej: {"min_pruebas": 2, "nota_minima": 65}',
    )

    class Meta:
        db_table = "eval_scheme_component"
        verbose_name = "Componente del esquema"
        verbose_name_plural = "Componentes del esquema"
        unique_together = [("esquema", "componente")]
        constraints = [
            models.CheckConstraint(
                check=models.Q(porcentaje__gte=0) & models.Q(porcentaje__lte=100),
                name="ck_eval_scheme_comp_pct_range",
            )
        ]

    def __str__(self):
        return f"{self.componente.codigo}: {self.porcentaje}%"

    def clean(self):
        if self.esquema_id and self.esquema.locked:
            raise ValidationError(
                "El esquema está bloqueado; no se pueden agregar ni modificar sus componentes."
            )
        if self.porcentaje is not None:
            if self.porcentaje < 0 or self.porcentaje > 100:
                raise ValidationError("El porcentaje debe estar entre 0 y 100.")
        super().clean()


# ═══════════════════════════════════════════════════════════════════════════
#  CATÁLOGO GLOBAL DE PERÍODOS
# ═══════════════════════════════════════════════════════════════════════════

class Periodo(models.Model):
    """
    Catálogo global de períodos de evaluación.
    Ejemplos: 1er Período, 2do Período, 3er Período.
    """
    nombre = models.CharField("Nombre", max_length=100)
    numero = models.PositiveSmallIntegerField("Número", unique=True)

    class Meta:
        db_table = "catalogos_periodo"
        verbose_name = "Período"
        verbose_name_plural = "Períodos"
        ordering = ("numero",)

    def __str__(self):
        return f"{self.numero}. {self.nombre}"

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.strip().upper()
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════
#  TABLAS INSTITUCIONALES
# ═══════════════════════════════════════════════════════════════════════════

class SubareaCursoLectivo(models.Model):
    """
    Tabla institucional: activa y liga una materia (subárea) a un curso lectivo
    dentro de una institución, asociándola al esquema de evaluación que aplica ese año.

    Extiende la lógica de catalogos.SubAreaInstitucion (que solo tiene institución)
    añadiendo granularidad por curso lectivo y el esquema de evaluación.
    """
    institucion = models.ForeignKey(
        "core.Institucion",
        on_delete=models.CASCADE,
        verbose_name="Institución",
        related_name="subareas_curso_lectivo",
    )
    curso_lectivo = models.ForeignKey(
        "catalogos.CursoLectivo",
        on_delete=models.CASCADE,
        verbose_name="Curso Lectivo",
        related_name="subareas_curso_lectivo",
    )
    subarea = models.ForeignKey(
        "catalogos.SubArea",
        on_delete=models.PROTECT,
        verbose_name="Subárea / Materia",
        related_name="subareas_curso_lectivo",
    )
    activa = models.BooleanField("Activa", default=True)
    eval_scheme = models.ForeignKey(
        EsquemaEval,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Esquema de evaluación",
        related_name="subareas_curso_lectivo",
    )

    class Meta:
        db_table = "config_institucional_subareacursolectivo"
        verbose_name = "Subárea por Curso Lectivo"
        verbose_name_plural = "Subáreas por Curso Lectivo"
        unique_together = [("institucion", "curso_lectivo", "subarea")]
        ordering = ("curso_lectivo__anio", "subarea__nombre")
        permissions = [
            ("access_subareas_curso", "Puede gestionar subáreas por curso lectivo"),
        ]

    def __str__(self):
        estado = "✓" if self.activa else "✗"
        return f"[{estado}] {self.subarea.nombre} | {self.curso_lectivo} | {self.institucion}"


class PeriodoCursoLectivo(models.Model):
    """
    Tabla institucional: períodos vigentes para una institución en un curso lectivo.
    Las calificaciones futuras referenciarán periodo_id de esta tabla.
    """
    institucion = models.ForeignKey(
        "core.Institucion",
        on_delete=models.CASCADE,
        verbose_name="Institución",
        related_name="periodos_curso_lectivo",
    )
    curso_lectivo = models.ForeignKey(
        "catalogos.CursoLectivo",
        on_delete=models.CASCADE,
        verbose_name="Curso Lectivo",
        related_name="periodos_curso_lectivo",
    )
    periodo = models.ForeignKey(
        Periodo,
        on_delete=models.PROTECT,
        verbose_name="Período",
        related_name="periodos_curso_lectivo",
    )
    fecha_inicio = models.DateField("Fecha de inicio", null=True, blank=True)
    fecha_fin = models.DateField("Fecha de fin", null=True, blank=True)
    activo = models.BooleanField("Activo", default=True)

    class Meta:
        db_table = "config_institucional_periodocursolectivo"
        verbose_name = "Período por Curso Lectivo"
        verbose_name_plural = "Períodos por Curso Lectivo"
        unique_together = [("institucion", "curso_lectivo", "periodo")]
        ordering = ("curso_lectivo__anio", "periodo__numero")
        permissions = [
            ("access_periodos_curso", "Puede gestionar períodos por curso lectivo"),
        ]

    def __str__(self):
        return f"{self.periodo.nombre} | {self.curso_lectivo} | {self.institucion}"

    def clean(self):
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin < self.fecha_inicio:
                raise ValidationError(
                    "La fecha de fin no puede ser anterior a la fecha de inicio."
                )
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DocenteAsignacion(models.Model):
    """
    Asignación anual de un docente a una materia (subárea) en una sección o subgrupo.

    Reglas de negocio:
    - Materia académica (subarea.es_academica=True):
        seccion_id NOT NULL y subgrupo_id MUST BE NULL.
    - Materia técnica (es_academica=False):
        subgrupo_id NOT NULL (seccion puede ser NULL o derivarse del subgrupo).

    Los porcentajes de evaluación vienen del eval_scheme ligado al subarea_curso
    y NO son editables por el docente. El snapshot se copia al crear la asignación
    para mantener histórico aunque el esquema cambie en el futuro.
    """
    docente = models.ForeignKey(
        "config_institucional.Profesor",
        on_delete=models.PROTECT,
        verbose_name="Docente",
        related_name="asignaciones",
    )
    subarea_curso = models.ForeignKey(
        SubareaCursoLectivo,
        on_delete=models.PROTECT,
        verbose_name="Subárea / Curso Lectivo",
        related_name="asignaciones",
    )
    curso_lectivo = models.ForeignKey(
        "catalogos.CursoLectivo",
        on_delete=models.PROTECT,
        verbose_name="Curso Lectivo",
        related_name="asignaciones_docente",
    )
    seccion = models.ForeignKey(
        "catalogos.Seccion",
        on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name="Sección",
        related_name="asignaciones_docente",
        help_text="Obligatorio para materias académicas; NULL para técnicas.",
    )
    subgrupo = models.ForeignKey(
        "catalogos.Subgrupo",
        on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name="Subgrupo",
        related_name="asignaciones_docente",
        help_text="Obligatorio para materias técnicas; NULL para académicas.",
    )
    activo = models.BooleanField("Activo", default=True)
    eval_scheme_snapshot = models.ForeignKey(
        EsquemaEval,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Esquema (snapshot histórico)",
        related_name="asignaciones_snapshot",
        help_text="Copia del esquema al crear la asignación. No cambia aunque el esquema se modifique.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "docente_asignacion"
        verbose_name = "Asignación Docente"
        verbose_name_plural = "Asignaciones Docentes"
        ordering = ("-curso_lectivo__anio", "docente__usuario__last_name")
        permissions = [
            ("access_docente_asignacion", "Puede gestionar asignaciones docentes"),
        ]

    def __str__(self):
        grupo = f"Secc. {self.seccion}" if self.seccion_id else f"Subgr. {self.subgrupo}"
        return (
            f"{self.docente} → {self.subarea_curso.subarea.nombre} | "
            f"{grupo} | {self.curso_lectivo}"
        )

    def clean(self):
        if not self.subarea_curso_id:
            return
        subarea = self.subarea_curso.subarea

        if subarea.es_academica:
            if not self.seccion_id:
                raise ValidationError(
                    f"La materia «{subarea.nombre}» es académica. Debe asignar una sección."
                )
            if self.subgrupo_id:
                raise ValidationError(
                    f"La materia «{subarea.nombre}» es académica. No se asigna por subgrupo."
                )
        else:
            if not self.subgrupo_id:
                raise ValidationError(
                    f"La materia «{subarea.nombre}» es técnica. Debe asignar un subgrupo."
                )

        # El docente debe pertenecer a la misma institución que el subarea_curso
        if self.docente_id and self.subarea_curso_id:
            if self.docente.institucion_id != self.subarea_curso.institucion_id:
                raise ValidationError(
                    "El docente no pertenece a la misma institución que la asignación."
                )

        # El curso lectivo debe coincidir con el del subarea_curso
        if self.curso_lectivo_id and self.subarea_curso_id:
            if self.curso_lectivo_id != self.subarea_curso.curso_lectivo_id:
                raise ValidationError(
                    "El curso lectivo no coincide con el del subárea-curso seleccionada."
                )

        super().clean()

    def save(self, *args, **kwargs):
        # Auto-snapshot del esquema al crear la asignación
        if not self.pk and not self.eval_scheme_snapshot_id and self.subarea_curso_id:
            self.eval_scheme_snapshot_id = self.subarea_curso.eval_scheme_id
        self.full_clean()
        super().save(*args, **kwargs)
