from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("config_institucional", "0005_remove_subgrupocursolectivo_tipo_estudiante"),
    ]

    operations = [
        migrations.AddField(
            model_name="profesor",
            name="max_asignaciones_override",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Solo aplica en Institución General. Vacío = usar el límite general de la institución.",
                null=True,
                verbose_name="Máximo de asignaciones (override)",
            ),
        ),
    ]
