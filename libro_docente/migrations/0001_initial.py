import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalogos", "0005_remove_seccion_tipo_estudiante_remove_subgrupo_tipo_estudiante"),
        ("core", "0001_initial"),
        ("evaluaciones", "0003_fix_trigger_column_name"),
        ("matricula", "0004_alter_matriculaacademica_options"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AsistenciaSesion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "docente_asignacion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sesiones_asistencia",
                        to="evaluaciones.docenteasignacion",
                        verbose_name="Asignación docente",
                    ),
                ),
                (
                    "institucion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sesiones_asistencia",
                        to="core.institucion",
                        verbose_name="Institución",
                    ),
                ),
                (
                    "curso_lectivo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sesiones_asistencia",
                        to="catalogos.cursolectivo",
                        verbose_name="Curso lectivo",
                    ),
                ),
                (
                    "periodo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sesiones_asistencia",
                        to="evaluaciones.periodo",
                        verbose_name="Período",
                    ),
                ),
                ("fecha", models.DateField(default=django.utils.timezone.localdate, db_index=True, verbose_name="Fecha")),
                ("sesion_numero", models.PositiveSmallIntegerField(default=1, verbose_name="N.° de sesión")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sesiones_asistencia_creadas",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Creado por",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Sesión de asistencia",
                "verbose_name_plural": "Sesiones de asistencia",
                "db_table": "asistencia_sesion",
                "ordering": ("fecha", "sesion_numero"),
                "permissions": [("access_libro_docente", "Puede acceder al Libro del Docente")],
            },
        ),
        migrations.AddConstraint(
            model_name="AsistenciaSesion",
            constraint=models.UniqueConstraint(
                fields=["docente_asignacion", "periodo", "fecha", "sesion_numero"],
                name="uniq_sesion_asistencia",
            ),
        ),
        migrations.AddIndex(
            model_name="AsistenciaSesion",
            index=models.Index(fields=["docente_asignacion", "fecha"], name="asis_ses_asig_fecha_idx"),
        ),
        migrations.AddIndex(
            model_name="AsistenciaSesion",
            index=models.Index(fields=["periodo", "fecha"], name="asis_ses_periodo_fecha_idx"),
        ),
        # ── AsistenciaRegistro ────────────────────────────────────────────
        migrations.CreateModel(
            name="AsistenciaRegistro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "sesion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registros",
                        to="libro_docente.asistenciasesion",
                        verbose_name="Sesión",
                    ),
                ),
                (
                    "estudiante",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registros_asistencia",
                        to="matricula.estudiante",
                        verbose_name="Estudiante",
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("P", "Presente"),
                            ("T", "Tardía"),
                            ("AI", "Ausente injustificada"),
                            ("AJ", "Ausente justificada"),
                        ],
                        default="AI",
                        max_length=2,
                        verbose_name="Estado",
                    ),
                ),
                ("observacion", models.CharField(blank=True, max_length=255, verbose_name="Observación")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Registro de asistencia",
                "verbose_name_plural": "Registros de asistencia",
                "db_table": "asistencia_registro",
            },
        ),
        migrations.AddConstraint(
            model_name="AsistenciaRegistro",
            constraint=models.UniqueConstraint(
                fields=["sesion", "estudiante"],
                name="uniq_registro_por_sesion_estudiante",
            ),
        ),
        migrations.AddIndex(
            model_name="AsistenciaRegistro",
            index=models.Index(fields=["sesion", "estudiante"], name="asis_reg_sesion_est_idx"),
        ),
    ]
