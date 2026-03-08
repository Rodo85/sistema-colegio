from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
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
    ALCANCE_TODOS = "TODOS"
    ALCANCE_REGULARES = "REGULARES"
    ALCANCE_ADECUACION = "ADECUACION"
    ALCANCE_CHOICES = [
        (ALCANCE_TODOS, "Asignar a todos"),
        (ALCANCE_REGULARES, "Asignar regulares"),
        (ALCANCE_ADECUACION, "Adecuación significativa"),
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
    alcance_estudiantes = models.CharField(
        "Alcance estudiantes",
        max_length=20,
        choices=ALCANCE_CHOICES,
        default=ALCANCE_TODOS,
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


class EstudianteOcultoAsignacion(models.Model):
    """
    Oculta estudiantes solo para una asignación docente específica
    (docente+materia+grupo), sin alterar matrícula oficial.
    """
    docente_asignacion = models.ForeignKey(
        "evaluaciones.DocenteAsignacion",
        on_delete=models.CASCADE,
        related_name="estudiantes_ocultos",
        verbose_name="Asignación docente",
    )
    estudiante = models.ForeignKey(
        "matricula.Estudiante",
        on_delete=models.PROTECT,
        related_name="ocultamientos_libro_docente",
        verbose_name="Estudiante",
    )
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ocultamientos_estudiantes_libro_docente",
        verbose_name="Creado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "libro_docente_estudiante_oculto"
        verbose_name = "Estudiante oculto por asignación"
        verbose_name_plural = "Estudiantes ocultos por asignación"
        constraints = [
            models.UniqueConstraint(
                fields=["docente_asignacion", "estudiante"],
                name="uniq_libro_doc_est_oculto",
            ),
        ]
        indexes = [
            models.Index(
                fields=["docente_asignacion", "estudiante"],
                name="libro_doc_est_oc_idx",
            ),
        ]

    def __str__(self):
        return f"{self.docente_asignacion_id} - {self.estudiante_id}"


class EstudianteAdecuacionAsignacion(models.Model):
    """
    Marca estudiantes con adecuación significativa para una asignación docente.
    """
    docente_asignacion = models.ForeignKey(
        "evaluaciones.DocenteAsignacion",
        on_delete=models.CASCADE,
        related_name="estudiantes_adecuacion",
        verbose_name="Asignación docente",
    )
    estudiante = models.ForeignKey(
        "matricula.Estudiante",
        on_delete=models.PROTECT,
        related_name="adecuaciones_libro_docente",
        verbose_name="Estudiante",
    )
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marcas_adecuacion_libro_docente",
        verbose_name="Creado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "libro_docente_estudiante_adecuacion"
        verbose_name = "Estudiante con adecuación por asignación"
        verbose_name_plural = "Estudiantes con adecuación por asignación"
        constraints = [
            models.UniqueConstraint(
                fields=["docente_asignacion", "estudiante"],
                name="uniq_libro_doc_est_adecuacion",
            ),
        ]
        indexes = [
            models.Index(
                fields=["docente_asignacion", "estudiante"],
                name="libro_doc_est_ad_idx",
            ),
        ]

    def __str__(self):
        return f"{self.docente_asignacion_id} - {self.estudiante_id}"


class EstudianteAdecuacionNoSignificativaAsignacion(models.Model):
    """
    Marca estudiantes con adecuación no significativa para una asignación docente.
    Se usa para reportes y logística; no cambia reglas de tareas/cotidianos.
    """
    docente_asignacion = models.ForeignKey(
        "evaluaciones.DocenteAsignacion",
        on_delete=models.CASCADE,
        related_name="estudiantes_adecuacion_no_significativa",
        verbose_name="Asignación docente",
    )
    estudiante = models.ForeignKey(
        "matricula.Estudiante",
        on_delete=models.PROTECT,
        related_name="adecuaciones_no_significativas_libro_docente",
        verbose_name="Estudiante",
    )
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marcas_adecuacion_no_significativa_libro_docente",
        verbose_name="Creado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "libro_docente_estudiante_adecuacion_no_sig"
        verbose_name = "Estudiante con adecuación no significativa por asignación"
        verbose_name_plural = "Estudiantes con adecuación no significativa por asignación"
        constraints = [
            models.UniqueConstraint(
                fields=["docente_asignacion", "estudiante"],
                name="uniq_libro_doc_est_adecuacion_no_sig",
            ),
        ]
        indexes = [
            models.Index(
                fields=["docente_asignacion", "estudiante"],
                name="libro_doc_est_ad_no_sig_idx",
            ),
        ]

    def __str__(self):
        return f"{self.docente_asignacion_id} - {self.estudiante_id}"


class ListaEstudiantesDocente(models.Model):
    """
    Lista privada de estudiantes por docente y grupo/subgrupo (Institución General).
    Se reutiliza entre materias del mismo grupo para el mismo docente.
    """
    docente = models.ForeignKey(
        "config_institucional.Profesor",
        on_delete=models.CASCADE,
        related_name="listas_estudiantes_docente",
        verbose_name="Docente",
    )
    institucion = models.ForeignKey(
        "core.Institucion",
        on_delete=models.PROTECT,
        related_name="listas_estudiantes_docente",
        verbose_name="Institución",
    )
    curso_lectivo = models.ForeignKey(
        "catalogos.CursoLectivo",
        on_delete=models.PROTECT,
        related_name="listas_estudiantes_docente",
        verbose_name="Curso lectivo",
    )
    seccion = models.ForeignKey(
        "catalogos.Seccion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="listas_estudiantes_docente",
        verbose_name="Sección",
    )
    subgrupo = models.ForeignKey(
        "catalogos.Subgrupo",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="listas_estudiantes_docente",
        verbose_name="Subgrupo",
    )
    created_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listas_estudiantes_docente_creadas",
        verbose_name="Creado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "libro_docente_lista_estudiantes_docente"
        verbose_name = "Lista privada de estudiantes (docente)"
        verbose_name_plural = "Listas privadas de estudiantes (docente)"
        constraints = [
            models.UniqueConstraint(
                fields=["docente", "curso_lectivo", "seccion"],
                condition=models.Q(subgrupo__isnull=True, seccion__isnull=False),
                name="uniq_libdoc_lista_doc_curso_seccion",
            ),
            models.UniqueConstraint(
                fields=["docente", "curso_lectivo", "subgrupo"],
                condition=models.Q(subgrupo__isnull=False),
                name="uniq_libdoc_lista_doc_curso_subgrupo",
            ),
        ]

    def __str__(self):
        if self.subgrupo_id:
            return f"{self.docente} · {self.subgrupo} · {self.curso_lectivo}"
        return f"{self.docente} · {self.seccion} · {self.curso_lectivo}"


class ListaEstudiantesDocenteItem(models.Model):
    lista = models.ForeignKey(
        ListaEstudiantesDocente,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Lista",
    )
    estudiante = models.ForeignKey(
        "matricula.Estudiante",
        on_delete=models.PROTECT,
        related_name="listas_docente_items",
        verbose_name="Estudiante",
    )
    orden = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "libro_docente_lista_estudiantes_docente_item"
        verbose_name = "Estudiante en lista privada"
        verbose_name_plural = "Estudiantes en lista privada"
        constraints = [
            models.UniqueConstraint(
                fields=["lista", "estudiante"],
                name="uniq_libdoc_lista_item",
            ),
        ]
        ordering = ("orden", "id")


class HorarioDocenteConfiguracion(models.Model):
    """
    Configuración simple de horario por docente.
    En Institución General se separa por centro de trabajo.
    """
    docente = models.ForeignKey(
        "config_institucional.Profesor",
        on_delete=models.CASCADE,
        related_name="horarios_docente",
        verbose_name="Docente",
    )
    institucion = models.ForeignKey(
        "core.Institucion",
        on_delete=models.PROTECT,
        related_name="horarios_docente",
        verbose_name="Institución",
    )
    centro_trabajo = models.ForeignKey(
        "evaluaciones.CentroTrabajo",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="horarios_docente",
        verbose_name="Centro de trabajo",
    )
    max_lecciones_dia = models.PositiveSmallIntegerField(
        "Máximo de lecciones por día",
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    receso_despues_leccion = models.CharField(
        "Recesos después de lección",
        max_length=120,
        blank=True,
        default="",
        help_text="Lista de lecciones separadas por coma. Ejemplo: 3,6 (receso entre 3-4 y 6-7).",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "libro_docente_horario_config"
        verbose_name = "Configuración de horario docente"
        verbose_name_plural = "Configuraciones de horario docente"
        constraints = [
            models.UniqueConstraint(
                fields=["docente", "centro_trabajo"],
                condition=models.Q(centro_trabajo__isnull=False),
                name="uniq_horario_docente_centro",
            ),
            models.UniqueConstraint(
                fields=["docente"],
                condition=models.Q(centro_trabajo__isnull=True),
                name="uniq_horario_docente_sin_centro",
            ),
        ]

    def __str__(self):
        if self.centro_trabajo_id:
            return f"{self.docente} · {self.centro_trabajo} ({self.max_lecciones_dia})"
        return f"{self.docente} · Horario ({self.max_lecciones_dia})"

    def clean(self):
        if self.docente_id and self.institucion_id and self.docente.institucion_id != self.institucion_id:
            raise ValidationError("La institución del horario debe coincidir con la del docente.")
        if self.centro_trabajo_id:
            if self.centro_trabajo.docente_id != self.docente_id:
                raise ValidationError("El centro de trabajo no pertenece al docente.")
            if self.centro_trabajo.institucion_id != self.institucion_id:
                raise ValidationError("El centro de trabajo no pertenece a la institución del horario.")
        if self.receso_despues_leccion:
            partes = [p.strip() for p in str(self.receso_despues_leccion).split(",") if p.strip()]
            for p in partes:
                if not p.isdigit():
                    raise ValidationError("Los recesos deben ser números de lección válidos.")
                n = int(p)
                if n < 1 or n >= self.max_lecciones_dia:
                    raise ValidationError("Cada receso debe quedar antes de la última lección del día.")
        super().clean()


class HorarioDocenteBloque(models.Model):
    """
    Bloque semanal simple: día + lección + asignación.
    """
    LUNES = 1
    MARTES = 2
    MIERCOLES = 3
    JUEVES = 4
    VIERNES = 5
    SABADO = 6
    DOMINGO = 7
    DIA_CHOICES = [
        (LUNES, "Lunes"),
        (MARTES, "Martes"),
        (MIERCOLES, "Miércoles"),
        (JUEVES, "Jueves"),
        (VIERNES, "Viernes"),
        (SABADO, "Sábado"),
        (DOMINGO, "Domingo"),
    ]

    configuracion = models.ForeignKey(
        HorarioDocenteConfiguracion,
        on_delete=models.CASCADE,
        related_name="bloques",
        verbose_name="Configuración de horario",
    )
    dia_semana = models.PositiveSmallIntegerField("Día de semana", choices=DIA_CHOICES)
    leccion_numero = models.PositiveSmallIntegerField("Lección")
    docente_asignacion = models.ForeignKey(
        "evaluaciones.DocenteAsignacion",
        on_delete=models.CASCADE,
        related_name="bloques_horario_docente",
        verbose_name="Asignación docente",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "libro_docente_horario_bloque"
        verbose_name = "Bloque de horario docente"
        verbose_name_plural = "Bloques de horario docente"
        ordering = ("dia_semana", "leccion_numero")
        constraints = [
            models.UniqueConstraint(
                fields=["configuracion", "dia_semana", "leccion_numero"],
                name="uniq_horario_docente_bloque",
            ),
        ]

    def __str__(self):
        return f"{self.get_dia_semana_display()} L{self.leccion_numero} · {self.docente_asignacion}"

    def clean(self):
        if self.leccion_numero < 1:
            raise ValidationError("La lección debe ser mayor o igual a 1.")
        if self.configuracion_id and self.leccion_numero > self.configuracion.max_lecciones_dia:
            raise ValidationError(
                f"La lección no puede exceder {self.configuracion.max_lecciones_dia} para esta configuración."
            )
        if self.configuracion_id and self.docente_asignacion_id:
            if self.docente_asignacion.docente_id != self.configuracion.docente_id:
                raise ValidationError("La asignación no pertenece al docente del horario.")
            if self.docente_asignacion.subarea_curso.institucion_id != self.configuracion.institucion_id:
                raise ValidationError("La asignación no pertenece a la institución del horario.")
            if self.configuracion.centro_trabajo_id:
                if self.docente_asignacion.centro_trabajo_id != self.configuracion.centro_trabajo_id:
                    raise ValidationError("La asignación no corresponde al centro de trabajo del horario.")
        super().clean()


class AsistenciaSesion(models.Model):
    """
    Representa una pasada de lista diaria de un docente para una asignación.
    La asistencia se registra una sola vez por fecha y se indica cuántas
    lecciones se impartieron ese día.
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
    lecciones = models.PositiveSmallIntegerField(
        "Lecciones del día",
        default=1,
        help_text="Cantidad de lecciones impartidas en la fecha registrada.",
    )
    minuta = models.CharField(
        "Minuta",
        max_length=1000,
        blank=True,
        default="",
        help_text="Observación general del día (máximo 1000 caracteres).",
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
                fields=["docente_asignacion", "fecha"],
                name="uniq_sesion_asistencia_por_fecha",
            ),
            models.CheckConstraint(
                check=models.Q(sesion_numero=1),
                name="asis_sesion_numero_unico_dia",
            ),
        ]
        indexes = [
            models.Index(fields=["docente_asignacion", "fecha"], name="asis_ses_asig_fecha_idx"),
            models.Index(fields=["periodo", "fecha"], name="asis_ses_periodo_fecha_idx"),
        ]
        permissions = [
            ("access_libro_docente", "Puede acceder al Libro del Docente"),
        ]

    def __str__(self):
        return f"{self.fecha} – {self.docente_asignacion_id}"


class AsistenciaRegistro(models.Model):
    """
    Registro individual de asistencia: un estudiante en una sesión.
    """
    PRESENTE = "P"
    TARDIA_MEDIA = "TM"
    TARDIA_COMPLETA = "TC"
    AUSENTE_INJUSTIFICADA = "AI"
    AUSENTE_JUSTIFICADA = "AJ"
    ESTADO_CHOICES = [
        (PRESENTE, "Presente completo"),
        (TARDIA_MEDIA, "Tardía injustificada (media ausencia)"),
        (TARDIA_COMPLETA, "Tardía injustificada (ausencia completa)"),
        (AUSENTE_INJUSTIFICADA, "Ausente injustificada"),
        (AUSENTE_JUSTIFICADA, "Ausencia justificada"),
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
    lecciones_injustificadas = models.DecimalField(
        "Lecciones injustificadas",
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Permite ajustar el cálculo exacto por estudiante en el día (pasos de 0.5).",
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

    def clean(self):
        super().clean()
        if self.lecciones_injustificadas is None:
            return
        valor = self.lecciones_injustificadas
        if valor < 0:
            raise ValidationError("Las lecciones injustificadas no pueden ser negativas.")
        lecciones_dia = (self.sesion.lecciones or 1) if self.sesion_id else 1
        if valor > lecciones_dia:
            raise ValidationError(f"Las lecciones injustificadas no pueden exceder {lecciones_dia}.")
        # Acepta incrementos de 0.5
        if (valor * 2) != (valor * 2).to_integral_value():
            raise ValidationError("Las lecciones injustificadas deben avanzar en pasos de 0.5.")
