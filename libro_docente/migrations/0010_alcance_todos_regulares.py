from django.db import migrations, models


def migrar_grupo_a_regulares(apps, schema_editor):
    ActividadEvaluacion = apps.get_model("libro_docente", "ActividadEvaluacion")
    ActividadEvaluacion.objects.filter(alcance_estudiantes="GRUPO").update(
        alcance_estudiantes="REGULARES"
    )


def revertir_regulares_a_grupo(apps, schema_editor):
    ActividadEvaluacion = apps.get_model("libro_docente", "ActividadEvaluacion")
    ActividadEvaluacion.objects.filter(alcance_estudiantes="REGULARES").update(
        alcance_estudiantes="GRUPO"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("libro_docente", "0009_adecuacion_y_alcance_actividad"),
    ]

    operations = [
        migrations.RunPython(migrar_grupo_a_regulares, revertir_regulares_a_grupo),
        migrations.AlterField(
            model_name="actividadevaluacion",
            name="alcance_estudiantes",
            field=models.CharField(
                choices=[
                    ("TODOS", "Asignar a todos"),
                    ("REGULARES", "Asignar regulares"),
                    ("ADECUACION", "Adecuación significativa"),
                ],
                default="TODOS",
                max_length=20,
                verbose_name="Alcance estudiantes",
            ),
        ),
    ]
