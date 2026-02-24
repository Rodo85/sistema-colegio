# Generated manually - Módulo de evaluación por indicadores (TAREAS/COTIDIANOS)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Crea modelos para evaluación por indicadores:
    - ActividadEvaluacion (actividad TAREA o COTIDIANO por asignación/periodo)
    - IndicadorActividad (indicadores con escala_min/escala_max)
    - PuntajeIndicador (puntaje por estudiante + indicador)
    """

    dependencies = [
        ("libro_docente", "0004_optimize_asistencia_indexes"),
        ("catalogos", "0005_remove_seccion_tipo_estudiante_remove_subgrupo_tipo_estudiante"),
        ("core", "0001_initial"),
        ("evaluaciones", "0003_fix_trigger_column_name"),
        ("matricula", "0004_alter_matriculaacademica_options"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ActividadEvaluacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "tipo_componente",
                    models.CharField(
                        choices=[("TAREA", "Tarea"), ("COTIDIANO", "Cotidiano")],
                        max_length=20,
                        verbose_name="Tipo",
                    ),
                ),
                ("titulo", models.CharField(max_length=200, verbose_name="Título")),
                ("descripcion", models.TextField(blank=True, verbose_name="Descripción")),
                ("fecha_asignacion", models.DateField(blank=True, null=True, verbose_name="Fecha asignación")),
                ("fecha_entrega", models.DateField(blank=True, null=True, verbose_name="Fecha entrega")),
                (
                    "estado",
                    models.CharField(
                        choices=[("BORRADOR", "Borrador"), ("ACTIVA", "Activa"), ("CERRADA", "Cerrada")],
                        default="BORRADOR",
                        max_length=20,
                        verbose_name="Estado",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "curso_lectivo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="actividades_evaluacion",
                        to="catalogos.cursolectivo",
                        verbose_name="Curso lectivo",
                    ),
                ),
                (
                    "docente_asignacion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="actividades_evaluacion",
                        to="evaluaciones.docenteasignacion",
                        verbose_name="Asignación docente",
                    ),
                ),
                (
                    "institucion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="actividades_evaluacion",
                        to="core.institucion",
                        verbose_name="Institución",
                    ),
                ),
                (
                    "periodo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="actividades_evaluacion",
                        to="evaluaciones.periodo",
                        verbose_name="Período",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="actividades_evaluacion_creadas",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Creado por",
                    ),
                ),
            ],
            options={
                "verbose_name": "Actividad de evaluación",
                "verbose_name_plural": "Actividades de evaluación",
                "db_table": "evaluacion_actividad",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="actividadevaluacion",
            index=models.Index(
                fields=["docente_asignacion", "periodo", "tipo_componente"],
                name="eval_act_asig_per_tipo_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="actividadevaluacion",
            index=models.Index(fields=["institucion", "periodo"], name="eval_act_inst_per_idx"),
        ),
        migrations.CreateModel(
            name="IndicadorActividad",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("orden", models.PositiveSmallIntegerField(default=0, verbose_name="Orden")),
                ("descripcion", models.TextField(verbose_name="Descripción")),
                ("escala_min", models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name="Escala mínima")),
                ("escala_max", models.DecimalField(decimal_places=2, default=5, max_digits=5, verbose_name="Escala máxima")),
                ("activo", models.BooleanField(default=True, verbose_name="Activo")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "actividad",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="indicadores",
                        to="libro_docente.actividadevaluacion",
                        verbose_name="Actividad",
                    ),
                ),
            ],
            options={
                "verbose_name": "Indicador de actividad",
                "verbose_name_plural": "Indicadores de actividad",
                "db_table": "evaluacion_indicador",
                "ordering": ("actividad", "orden", "id"),
            },
        ),
        migrations.AddConstraint(
            model_name="indicadoractividad",
            constraint=models.CheckConstraint(
                check=models.Q(("escala_max__gte", models.F("escala_min"))),
                name="ck_eval_ind_escala_max_gte_min",
            ),
        ),
        migrations.CreateModel(
            name="PuntajeIndicador",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "puntaje_obtenido",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Debe estar entre escala_min y escala_max del indicador.",
                        max_digits=5,
                        null=True,
                        verbose_name="Puntaje obtenido",
                    ),
                ),
                ("observacion", models.CharField(blank=True, max_length=255, verbose_name="Observación")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "estudiante",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="puntajes_indicadores",
                        to="matricula.estudiante",
                        verbose_name="Estudiante",
                    ),
                ),
                (
                    "indicador",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="puntajes",
                        to="libro_docente.indicadoractividad",
                        verbose_name="Indicador",
                    ),
                ),
            ],
            options={
                "verbose_name": "Puntaje por indicador",
                "verbose_name_plural": "Puntajes por indicador",
                "db_table": "evaluacion_puntaje",
            },
        ),
        migrations.AddConstraint(
            model_name="puntajeindicador",
            constraint=models.UniqueConstraint(
                fields=["indicador", "estudiante"],
                name="uniq_puntaje_indicador_estudiante",
            ),
        ),
        migrations.AddIndex(
            model_name="puntajeindicador",
            index=models.Index(fields=["indicador", "estudiante"], name="eval_punt_ind_est_idx"),
        ),
    ]
