from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("libro_docente", "0012_asistencia_sesion_unica_por_fecha"),
    ]

    operations = [
        migrations.AddField(
            model_name="asistenciaregistro",
            name="lecciones_injustificadas",
            field=models.DecimalField(
                blank=True,
                decimal_places=1,
                help_text="Permite ajustar el cálculo exacto por estudiante en el día (pasos de 0.5).",
                max_digits=5,
                null=True,
                verbose_name="Lecciones injustificadas",
            ),
        ),
    ]
