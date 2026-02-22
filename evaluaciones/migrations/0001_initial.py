import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalogos", "__first__"),
        ("config_institucional", "__first__"),
        ("core", "__first__"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── 1. eval_component ─────────────────────────────────────────────
        migrations.CreateModel(
            name="ComponenteEval",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=30, unique=True, verbose_name="Código")),
                ("nombre", models.CharField(max_length=100, verbose_name="Nombre")),
                ("descripcion", models.TextField(blank=True, verbose_name="Descripción")),
                ("activo", models.BooleanField(default=True, verbose_name="Activo")),
            ],
            options={
                "verbose_name": "Componente de evaluación",
                "verbose_name_plural": "Componentes de evaluación",
                "db_table": "eval_component",
                "ordering": ("nombre",),
            },
        ),
        # ── 2. eval_scheme ────────────────────────────────────────────────
        migrations.CreateModel(
            name="EsquemaEval",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=150, verbose_name="Nombre")),
                (
                    "tipo",
                    models.CharField(
                        choices=[("ACADEMICO", "Académico"), ("TECNICO", "Técnico")],
                        max_length=10,
                        verbose_name="Tipo",
                    ),
                ),
                (
                    "modalidad",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="esquemas_eval",
                        to="catalogos.modalidad",
                        verbose_name="Modalidad",
                    ),
                ),
                (
                    "especialidad",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="esquemas_eval",
                        to="catalogos.especialidad",
                        verbose_name="Especialidad",
                    ),
                ),
                ("vigente_desde", models.DateField(blank=True, null=True, verbose_name="Vigente desde")),
                ("vigente_hasta", models.DateField(blank=True, null=True, verbose_name="Vigente hasta")),
                (
                    "locked",
                    models.BooleanField(
                        default=False,
                        help_text="Si está bloqueado no se pueden editar sus componentes y la suma de porcentajes debe ser exactamente 100%.",
                        verbose_name="Bloqueado",
                    ),
                ),
                ("activo", models.BooleanField(default=True, verbose_name="Activo")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Esquema de evaluación",
                "verbose_name_plural": "Esquemas de evaluación",
                "db_table": "eval_scheme",
                "ordering": ("tipo", "nombre"),
            },
        ),
        # ── 3. eval_scheme_component ──────────────────────────────────────
        migrations.CreateModel(
            name="EsquemaEvalComponente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "esquema",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="componentes_esquema",
                        to="evaluaciones.esquemaeval",
                        verbose_name="Esquema",
                    ),
                ),
                (
                    "componente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="esquemas",
                        to="evaluaciones.componenteeval",
                        verbose_name="Componente",
                    ),
                ),
                (
                    "porcentaje",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Valor entre 0.00 y 100.00.",
                        max_digits=5,
                        verbose_name="Porcentaje (%)",
                    ),
                ),
                (
                    "reglas_json",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Ej: {"min_pruebas": 2, "nota_minima": 65}',
                        verbose_name="Reglas adicionales",
                    ),
                ),
            ],
            options={
                "verbose_name": "Componente del esquema",
                "verbose_name_plural": "Componentes del esquema",
                "db_table": "eval_scheme_component",
            },
        ),
        migrations.AddConstraint(
            model_name="EsquemaEvalComponente",
            constraint=models.CheckConstraint(
                check=models.Q(porcentaje__gte=0) & models.Q(porcentaje__lte=100),
                name="ck_eval_scheme_comp_pct_range",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="EsquemaEvalComponente",
            unique_together={("esquema", "componente")},
        ),
        # ── 4. catalogos_periodo ──────────────────────────────────────────
        migrations.CreateModel(
            name="Periodo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100, verbose_name="Nombre")),
                ("numero", models.PositiveSmallIntegerField(unique=True, verbose_name="Número")),
            ],
            options={
                "verbose_name": "Período",
                "verbose_name_plural": "Períodos",
                "db_table": "catalogos_periodo",
                "ordering": ("numero",),
            },
        ),
        # ── 5. config_institucional_subareacursolectivo ───────────────────
        migrations.CreateModel(
            name="SubareaCursoLectivo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "institucion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subareas_curso_lectivo",
                        to="core.institucion",
                        verbose_name="Institución",
                    ),
                ),
                (
                    "curso_lectivo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subareas_curso_lectivo",
                        to="catalogos.cursolectivo",
                        verbose_name="Curso Lectivo",
                    ),
                ),
                (
                    "subarea",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subareas_curso_lectivo",
                        to="catalogos.subarea",
                        verbose_name="Subárea / Materia",
                    ),
                ),
                ("activa", models.BooleanField(default=True, verbose_name="Activa")),
                (
                    "eval_scheme",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="subareas_curso_lectivo",
                        to="evaluaciones.esquemaeval",
                        verbose_name="Esquema de evaluación",
                    ),
                ),
            ],
            options={
                "verbose_name": "Subárea por Curso Lectivo",
                "verbose_name_plural": "Subáreas por Curso Lectivo",
                "db_table": "config_institucional_subareacursolectivo",
                "ordering": ("curso_lectivo__anio", "subarea__nombre"),
            },
        ),
        migrations.AlterUniqueTogether(
            name="SubareaCursoLectivo",
            unique_together={("institucion", "curso_lectivo", "subarea")},
        ),
        migrations.AddIndex(
            model_name="SubareaCursoLectivo",
            index=models.Index(
                fields=["institucion", "curso_lectivo", "activa"],
                name="eval_scl_inst_cl_activa_idx",
            ),
        ),
        # ── 6. config_institucional_periodocursolectivo ───────────────────
        migrations.CreateModel(
            name="PeriodoCursoLectivo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "institucion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="periodos_curso_lectivo",
                        to="core.institucion",
                        verbose_name="Institución",
                    ),
                ),
                (
                    "curso_lectivo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="periodos_curso_lectivo",
                        to="catalogos.cursolectivo",
                        verbose_name="Curso Lectivo",
                    ),
                ),
                (
                    "periodo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="periodos_curso_lectivo",
                        to="evaluaciones.periodo",
                        verbose_name="Período",
                    ),
                ),
                ("fecha_inicio", models.DateField(blank=True, null=True, verbose_name="Fecha de inicio")),
                ("fecha_fin", models.DateField(blank=True, null=True, verbose_name="Fecha de fin")),
                ("activo", models.BooleanField(default=True, verbose_name="Activo")),
            ],
            options={
                "verbose_name": "Período por Curso Lectivo",
                "verbose_name_plural": "Períodos por Curso Lectivo",
                "db_table": "config_institucional_periodocursolectivo",
                "ordering": ("curso_lectivo__anio", "periodo__numero"),
            },
        ),
        migrations.AlterUniqueTogether(
            name="PeriodoCursoLectivo",
            unique_together={("institucion", "curso_lectivo", "periodo")},
        ),
        # ── 7. docente_asignacion ─────────────────────────────────────────
        migrations.CreateModel(
            name="DocenteAsignacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "docente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="asignaciones",
                        to="config_institucional.profesor",
                        verbose_name="Docente",
                    ),
                ),
                (
                    "subarea_curso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="asignaciones",
                        to="evaluaciones.subareacursolectivo",
                        verbose_name="Subárea / Curso Lectivo",
                    ),
                ),
                (
                    "curso_lectivo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="asignaciones_docente",
                        to="catalogos.cursolectivo",
                        verbose_name="Curso Lectivo",
                    ),
                ),
                (
                    "seccion",
                    models.ForeignKey(
                        blank=True,
                        help_text="Obligatorio para materias académicas; NULL para técnicas.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="asignaciones_docente",
                        to="catalogos.seccion",
                        verbose_name="Sección",
                    ),
                ),
                (
                    "subgrupo",
                    models.ForeignKey(
                        blank=True,
                        help_text="Obligatorio para materias técnicas; NULL para académicas.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="asignaciones_docente",
                        to="catalogos.subgrupo",
                        verbose_name="Subgrupo",
                    ),
                ),
                ("activo", models.BooleanField(default=True, verbose_name="Activo")),
                (
                    "eval_scheme_snapshot",
                    models.ForeignKey(
                        blank=True,
                        help_text="Copia del esquema al crear la asignación. No cambia aunque el esquema se modifique.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="asignaciones_snapshot",
                        to="evaluaciones.esquemaeval",
                        verbose_name="Esquema (snapshot histórico)",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Asignación Docente",
                "verbose_name_plural": "Asignaciones Docentes",
                "db_table": "docente_asignacion",
                "ordering": ("-curso_lectivo__anio", "docente__usuario__last_name"),
            },
        ),
        migrations.AddIndex(
            model_name="DocenteAsignacion",
            index=models.Index(
                fields=["curso_lectivo", "docente", "activo"],
                name="eval_da_cl_docente_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="DocenteAsignacion",
            index=models.Index(
                fields=["subarea_curso", "seccion"],
                name="eval_da_scl_seccion_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="DocenteAsignacion",
            index=models.Index(
                fields=["subarea_curso", "subgrupo"],
                name="eval_da_scl_subgrupo_idx",
            ),
        ),
        # ── 8. Trigger PostgreSQL: validar suma = 100 cuando locked ───────
        migrations.RunSQL(
            sql="""
CREATE OR REPLACE FUNCTION fn_eval_check_porcentaje_sum()
RETURNS TRIGGER AS $$
DECLARE
    v_scheme_id BIGINT;
    v_total     NUMERIC;
    v_locked    BOOLEAN;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_scheme_id := OLD.scheme_id;
    ELSE
        v_scheme_id := NEW.scheme_id;
    END IF;

    SELECT locked INTO v_locked
    FROM eval_scheme
    WHERE id = v_scheme_id;

    IF v_locked THEN
        SELECT COALESCE(SUM(porcentaje), 0) INTO v_total
        FROM eval_scheme_component
        WHERE scheme_id = v_scheme_id;

        IF v_total <> 100 THEN
            RAISE EXCEPTION
                'Esquema bloqueado: la suma de porcentajes debe ser 100 (actual: %).',
                v_total;
        END IF;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_eval_check_porcentaje_sum
AFTER INSERT OR UPDATE OR DELETE ON eval_scheme_component
FOR EACH ROW EXECUTE FUNCTION fn_eval_check_porcentaje_sum();
""",
            reverse_sql="""
DROP TRIGGER IF EXISTS trg_eval_check_porcentaje_sum ON eval_scheme_component;
DROP FUNCTION IF EXISTS fn_eval_check_porcentaje_sum();
""",
        ),
    ]
