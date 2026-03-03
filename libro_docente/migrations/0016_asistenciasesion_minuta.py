from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("libro_docente", "0015_alter_actividadevaluacion_tipo_componente"),
    ]

    operations = [
        migrations.AddField(
            model_name="asistenciasesion",
            name="minuta",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Observación general del día (máximo 200 caracteres).",
                max_length=200,
                verbose_name="Minuta",
            ),
        ),
    ]
