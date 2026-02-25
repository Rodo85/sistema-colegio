from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


# ═══════════════════════════════════════════════════════════════════════════
#  EVALUACIÓN POR INDICADORES (TAREAS / COTIDIANOS)
# ═══════════════════════════════════════════════════════════════════════════


class ActividadEvaluacion(models.Model):
    """
    Actividad de evaluación (TAREA o COTIDIANO) asociada a una asignación docente.
    Pertenece a institución, periodo y grupo/subgrupo vía docente_asignacion.
    """
    TAREA = "TAREA"
    COTIDIANO = "COTIDIANO"
    PRUEBA = "PRUEBA"
    PROYECTO = "PROYECTO"
    TIPO_CHOICES = [
        (TAREA, "Tarea"),
        (COTIDIANO, "Cotidiano"),
        (PRUEBA, "Prueba"),
        (PROYECTO, "Proyecto"),
    ]
    BORRADOR = "BORRADOR"
    ACTIVA = "ACTIVA"
    CERRADA = "CERRADA"
    ESTADO_CHOICES = [
        (BORRADOR, "Borrador"),
        (ACTIVA, "Activa"),
        (CERRADA, "Cerrada"),
    ]

    docente_asignacion = models.ForeignKey(
        "evaluaciones.DocenteAsignacion",
        on_delete=models.PROTECT,
        related_name="actividades_evaluacion",
        verbose_name="Asignación docente",
    )
    institucion = models.ForeignKey(
        "core.Institucion",
        on_delete=models.PROTECT,
        related_name="actividades_evaluacion",
        verbose_name="Institución",
    )
    curso_lectivo = models.ForeignKey(
        "catalogos.CursoLectivo",
        on_delete=models.PROTECT,
        related_name="actividades_evaluacion",
        verbose_name="Curso lectivo",
    )
    periodo = models.ForeignKey(
        "evaluaciones.Periodo",
        on_delete=models.PROTECT,
        related_name="actividades_evaluacion",
        verbose_name="Período",
    )
    tipo_componente = models.CharField(
        "Tipo",
        max_length=20,
        choices=TIPO_CHOICES,
    )
    titulo = models.CharField("Título", max_length=200)
    descripcion = models.TextField("Descripción", blank=True)
    puntaje_total = models.DecimalField(
        "Valor en puntos",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Solo para Prueba/Proyecto.",
    )
    porcentaje_actividad = models.DecimalField(
        "Valor en porcentaje",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Solo para Prueba/Proyecto.",
    )
    fecha_asignacion = models.DateField("Fecha asignación", null=True, blank=True)
    fecha_entrega = models.DateField("Fecha entrega", null=True, blank=True)
    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=ESTADO_CHOICES,
        default=BORRADOR,
    )
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="actividades_evaluacion_creadas",
        verbose_name="Creado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evaluacion_actividad"
        verbose_name = "Actividad de evaluación"
        verbose_name_plural = "Actividades de evaluación"
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=["docente_asignacion", "periodo", "tipo_componente"],
                name="eval_act_asig_per_tipo_idx",
            ),
            models.Index(fields=["institucion", "periodo"], name="eval_act_inst_per_idx"),
        ]

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_componente_display()})"

    def clean(self):
        if self.fecha_asignacion and self.fecha_entrega:
            if self.fecha_entrega < self.fecha_asignacion:
                raise ValidationError(
                    "La fecha de entrega no puede ser anterior a la fecha de asignación."
                )
        if self.docente_asignacion_id and self.institucion_id:
            if self.docente_asignacion.subarea_curso.institucion_id != self.institucion_id:
                raise ValidationError(
                    "La institución debe coincidir con la de la asignación docente."
                )
        es_simple = self.tipo_componente in (self.PRUEBA, self.PROYECTO)
        if es_simple:
            if self.puntaje_total is None or self.puntaje_total <= 0:
                raise ValidationError("En Prueba/Proyecto el valor en puntos debe ser mayor a 0.")
            if self.porcentaje_actividad is None or self.porcentaje_actividad <= 0:
                raise ValidationError("En Prueba/Proyecto el valor en porcentaje debe ser mayor a 0.")
            if self.puntaje_total != self.puntaje_total.to_integral_value():
                raise ValidationError("El valor en puntos debe ser entero (sin decimales).")
            if self.porcentaje_actividad != self.porcentaje_actividad.to_integral_value():
                raise ValidationError("El valor en porcentaje debe ser entero (sin decimales).")
        else:
            self.puntaje_total = None
            self.porcentaje_actividad = None
        super().clean()


class IndicadorActividad(models.Model):
    """
    Indicador de una actividad de evaluación.
    Define descripción y rango de puntaje (escala_min a escala_max).
    """
    actividad = models.ForeignKey(
        ActividadEvaluacion,
        on_delete=models.CASCADE,
        related_name="indicadores",
        verbose_name="Actividad",
    )
    orden = models.PositiveSmallIntegerField("Orden", default=0)
    descripcion = models.TextField("Descripción")
    escala_min = models.DecimalField(
        "Escala mínima",
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    escala_max = models.DecimalField(
        "Escala máxima",
        max_digits=5,
        decimal_places=2,
        default=5,
    )
    activo = models.BooleanField("Activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evaluacion_indicador"
        verbose_name = "Indicador de actividad"
        verbose_name_plural = "Indicadores de actividad"
        ordering = ("actividad", "orden", "id")
        constraints = [
            models.CheckConstraint(
                check=models.Q(escala_max__gte=models.F("escala_min")),
                name="ck_eval_ind_escala_max_gte_min",
            ),
        ]

    def __str__(self):
        desc = (self.descripcion or "")[:50]
        if len(self.descripcion or "") > 50:
            desc += "…"
        return f"{desc} ({self.escala_min}-{self.escala_max})"

    def clean(self):
        if self.escala_max is not None and self.escala_min is not None:
            if self.escala_max < self.escala_min:
                raise ValidationError("escala_max debe ser >= escala_min.")
        min_permitido = 0
        if self.actividad_id and self.actividad.tipo_componente == ActividadEvaluacion.COTIDIANO:
            min_permitido = 1
        if self.escala_min is not None:
            if self.escala_min < min_permitido:
                raise ValidationError(f"escala_min debe ser >= {min_permitido}.")
            if self.escala_min != self.escala_min.to_integral_value():
                raise ValidationError("escala_min debe ser entero (sin decimales).")
        if self.escala_max is not None:
            if self.escala_max < 0:
                raise ValidationError("escala_max debe ser >= 0.")
            if self.escala_max != self.escala_max.to_integral_value():
                raise ValidationError("escala_max debe ser entero (sin decimales).")
        super().clean()


class PuntajeIndicador(models.Model):
    """
    Puntaje obtenido por un estudiante en un indicador.
    Un indicador pertenece a una actividad; el estudiante debe estar en el grupo.
    """
    indicador = models.ForeignKey(
        IndicadorActividad,
        on_delete=models.CASCADE,
        related_name="puntajes",
        verbose_name="Indicador",
    )
    estudiante = models.ForeignKey(
        "matricula.Estudiante",
        on_delete=models.PROTECT,
        related_name="puntajes_indicadores",
        verbose_name="Estudiante",
    )
    puntaje_obtenido = models.DecimalField(
        "Puntaje obtenido",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Debe estar entre escala_min y escala_max del indicador.",
    )
    observacion = models.CharField("Observación", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evaluacion_puntaje"
        verbose_name = "Puntaje por indicador"
        verbose_name_plural = "Puntajes por indicador"
        constraints = [
            models.UniqueConstraint(
                fields=["indicador", "estudiante"],
                name="uniq_puntaje_indicador_estudiante",
            ),
        ]
        indexes = [
            models.Index(
                fields=["indicador", "estudiante"],
                name="eval_punt_ind_est_idx",
            ),
        ]

    def __str__(self):
        return f"{self.estudiante} – {self.indicador_id}: {self.puntaje_obtenido}"

    def clean(self):
        if self.puntaje_obtenido is not None and self.indicador_id:
            ind = self.indicador
            if self.puntaje_obtenido < 0:
                raise ValidationError("El puntaje debe ser >= 0.")
            if self.puntaje_obtenido != self.puntaje_obtenido.to_integral_value():
                raise ValidationError("El puntaje debe ser entero (sin decimales).")
            if ind.escala_min is not None and self.puntaje_obtenido < ind.escala_min:
                raise ValidationError(
                    f"El puntaje {self.puntaje_obtenido} debe ser >= {ind.escala_min}."
                )
            if ind.escala_max is not None and self.puntaje_obtenido > ind.escala_max:
                raise ValidationError(
                    f"El puntaje {self.puntaje_obtenido} debe ser <= {ind.escala_max}."
                )
        super().clean()


class ObservacionActividadEstudiante(models.Model):
    """
    Observación general por estudiante para una actividad (no por indicador).
    Útil para revisión y respaldo ante reclamos.
    """
    actividad = models.ForeignKey(
        ActividadEvaluacion,
        on_delete=models.CASCADE,
        related_name="observaciones_estudiantes",
        verbose_name="Actividad",
    )
    estudiante = models.ForeignKey(
        "matricula.Estudiante",
        on_delete=models.PROTECT,
        related_name="observaciones_actividad",
        verbose_name="Estudiante",
    )
    observacion = models.TextField("Observación", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evaluacion_observacion_estudiante"
        verbose_name = "Observación por estudiante en actividad"
        verbose_name_plural = "Observaciones por estudiante en actividad"
        constraints = [
            models.UniqueConstraint(
                fields=["actividad", "estudiante"],
                name="uniq_obs_actividad_estudiante",
            )
        ]
        indexes = [
            models.Index(
                fields=["actividad", "estudiante"],
                name="eval_obs_act_est_idx",
            ),
        ]

    def __str__(self):
        return f"{self.estudiante} – {self.actividad_id}"


class PuntajeSimple(models.Model):
    """
    Puntaje por estudiante para Prueba/Proyecto (sin indicadores).
    """
    actividad = models.ForeignKey(
        ActividadEvaluacion,
        on_delete=models.CASCADE,
        related_name="puntajes_simples",
        verbose_name="Actividad",
    )
    estudiante = models.ForeignKey(
        "matricula.Estudiante",
        on_delete=models.PROTECT,
        related_name="puntajes_simples",
        verbose_name="Estudiante",
    )
    puntos_obtenidos = models.DecimalField(
        "Puntos obtenidos",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evaluacion_puntaje_simple"
        verbose_name = "Puntaje simple (Prueba/Proyecto)"
        verbose_name_plural = "Puntajes simples"
        constraints = [
            models.UniqueConstraint(
                fields=["actividad", "estudiante"],
                name="uniq_puntaje_simple_act_est",
            ),
        ]
        indexes = [
            models.Index(fields=["actividad", "estudiante"], name="eval_ps_act_est_idx"),
        ]

    def __str__(self):
        return f"{self.estudiante} – {self.actividad_id}: {self.puntos_obtenidos}"

    def clean(self):
        if self.puntos_obtenidos is not None:
            if self.puntos_obtenidos < 0:
                raise ValidationError("Los puntos obtenidos deben ser >= 0.")
            if self.puntos_obtenidos != self.puntos_obtenidos.to_integral_value():
                raise ValidationError("Los puntos obtenidos deben ser enteros (sin decimales).")
            if self.actividad_id and self.actividad.puntaje_total is not None:
                if self.puntos_obtenidos > self.actividad.puntaje_total:
                    raise ValidationError(
                        f"Los puntos obtenidos deben ser <= {self.actividad.puntaje_total}."
                    )
        super().clean()


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
            models.Index(
                fields=["sesion", "estudiante", "estado"],
                name="asis_reg_sesion_est_estado_idx",
            ),
        ]

    def __str__(self):
        return f"{self.estudiante} – {self.get_estado_display()} ({self.sesion.fecha})"
