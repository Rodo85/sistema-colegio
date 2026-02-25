from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("libro_docente", "0005_evaluacion_actividades_indicadores"),
    ]

    operations = [
        migrations.CreateModel(
            name="ObservacionActividadEstudiante",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("observacion", models.TextField(blank=True, verbose_name="Observación")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("actividad", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="observaciones_estudiantes", to="libro_docente.actividadevaluacion", verbose_name="Actividad")),
                ("estudiante", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="observaciones_actividad", to="matricula.estudiante", verbose_name="Estudiante")),
            ],
            options={
                "verbose_name": "Observación por estudiante en actividad",
                "verbose_name_plural": "Observaciones por estudiante en actividad",
                "db_table": "evaluacion_observacion_estudiante",
            },
        ),
        migrations.AddConstraint(
            model_name="observacionactividadestudiante",
            constraint=models.UniqueConstraint(fields=("actividad", "estudiante"), name="uniq_obs_actividad_estudiante"),
        ),
        migrations.AddIndex(
            model_name="observacionactividadestudiante",
            index=models.Index(fields=["actividad", "estudiante"], name="eval_obs_act_est_idx"),
        ),
    ]
