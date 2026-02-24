# Generated manually - Componentes PRUEBA/PROYECTO y exclusión por asignación

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("libro_docente", "0005_evaluacion_actividades_indicadores"),
        ("evaluaciones", "0003_fix_trigger_column_name"),
        ("matricula", "0004_alter_matriculaacademica_options"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="actividadevaluacion",
            name="tipo_componente",
            field=models.CharField(
                choices=[
                    ("TAREA", "Tarea"),
                    ("COTIDIANO", "Cotidiano"),
                    ("PRUEBA", "Prueba"),
                    ("PROYECTO", "Proyecto"),
                ],
                max_length=20,
                verbose_name="Tipo",
            ),
        ),
        migrations.CreateModel(
            name="ExclusionEstudianteAsignacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("motivo", models.CharField(blank=True, max_length=255, verbose_name="Motivo")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="exclusiones_estudiantes_creadas",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Creado por",
                    ),
                ),
                (
                    "docente_asignacion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exclusiones_estudiantes_libro",
                        to="evaluaciones.docenteasignacion",
                        verbose_name="Asignación docente",
                    ),
                ),
                (
                    "estudiante",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exclusiones_asignacion_libro",
                        to="matricula.estudiante",
                        verbose_name="Estudiante",
                    ),
                ),
            ],
            options={
                "verbose_name": "Exclusión de estudiante por asignación",
                "verbose_name_plural": "Exclusiones de estudiantes por asignación",
                "db_table": "libro_exclusion_estudiante_asignacion",
            },
        ),
        migrations.AddConstraint(
            model_name="exclusionestudianteasignacion",
            constraint=models.UniqueConstraint(
                fields=("docente_asignacion", "estudiante"),
                name="uniq_libro_exclusion_asig_est",
            ),
        ),
        migrations.AddIndex(
            model_name="exclusionestudianteasignacion",
            index=models.Index(
                fields=["docente_asignacion", "estudiante"],
                name="libro_excl_asig_est_idx",
            ),
        ),
    ]
