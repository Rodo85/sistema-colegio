from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("libro_docente", "0006_observacion_actividad_estudiante"),
    ]

    operations = [
        migrations.AddField(
            model_name="actividadevaluacion",
            name="porcentaje_actividad",
            field=models.DecimalField(blank=True, decimal_places=2, help_text="Solo para Prueba/Proyecto.", max_digits=5, null=True, verbose_name="Valor en porcentaje"),
        ),
        migrations.AddField(
            model_name="actividadevaluacion",
            name="puntaje_total",
            field=models.DecimalField(blank=True, decimal_places=2, help_text="Solo para Prueba/Proyecto.", max_digits=6, null=True, verbose_name="Valor en puntos"),
        ),
        migrations.CreateModel(
            name="PuntajeSimple",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("puntos_obtenidos", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name="Puntos obtenidos")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("actividad", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="puntajes_simples", to="libro_docente.actividadevaluacion", verbose_name="Actividad")),
                ("estudiante", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="puntajes_simples", to="matricula.estudiante", verbose_name="Estudiante")),
            ],
            options={
                "verbose_name": "Puntaje simple (Prueba/Proyecto)",
                "verbose_name_plural": "Puntajes simples",
                "db_table": "evaluacion_puntaje_simple",
            },
        ),
        migrations.AddConstraint(
            model_name="puntajesimple",
            constraint=models.UniqueConstraint(fields=("actividad", "estudiante"), name="uniq_puntaje_simple_act_est"),
        ),
        migrations.AddIndex(
            model_name="puntajesimple",
            index=models.Index(fields=["actividad", "estudiante"], name="eval_ps_act_est_idx"),
        ),
    ]
