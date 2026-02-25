from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("evaluaciones", "0003_fix_trigger_column_name"),
        ("matricula", "0004_alter_matriculaacademica_options"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("libro_docente", "0008_estudianteocultoasignacion"),
    ]

    operations = [
        migrations.AddField(
            model_name="actividadevaluacion",
            name="alcance_estudiantes",
            field=models.CharField(
                choices=[
                    ("GRUPO", "Grupo (sin adecuación)"),
                    ("ADECUACION", "Adecuación significativa"),
                ],
                default="GRUPO",
                max_length=20,
                verbose_name="Alcance estudiantes",
            ),
        ),
        migrations.CreateModel(
            name="EstudianteAdecuacionAsignacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="marcas_adecuacion_libro_docente", to=settings.AUTH_USER_MODEL, verbose_name="Creado por")),
                ("docente_asignacion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="estudiantes_adecuacion", to="evaluaciones.docenteasignacion", verbose_name="Asignación docente")),
                ("estudiante", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="adecuaciones_libro_docente", to="matricula.estudiante", verbose_name="Estudiante")),
            ],
            options={
                "verbose_name": "Estudiante con adecuación por asignación",
                "verbose_name_plural": "Estudiantes con adecuación por asignación",
                "db_table": "libro_docente_estudiante_adecuacion",
            },
        ),
        migrations.AddConstraint(
            model_name="estudianteadecuacionasignacion",
            constraint=models.UniqueConstraint(fields=("docente_asignacion", "estudiante"), name="uniq_libro_doc_est_adecuacion"),
        ),
        migrations.AddIndex(
            model_name="estudianteadecuacionasignacion",
            index=models.Index(fields=["docente_asignacion", "estudiante"], name="libro_doc_est_ad_idx"),
        ),
    ]
