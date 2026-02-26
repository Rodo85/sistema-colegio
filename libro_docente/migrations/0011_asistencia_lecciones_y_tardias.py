from django.db import migrations, models


def map_tardia_legacy(apps, schema_editor):
    AsistenciaRegistro = apps.get_model("libro_docente", "AsistenciaRegistro")
    AsistenciaRegistro.objects.filter(estado="T").update(estado="TM")


class Migration(migrations.Migration):

    dependencies = [
        ("libro_docente", "0010_alcance_todos_regulares"),
    ]

    operations = [
        migrations.AddField(
            model_name="asistenciasesion",
            name="lecciones",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Cantidad de lecciones impartidas en la fecha registrada.",
                verbose_name="Lecciones del día",
            ),
        ),
        migrations.AlterField(
            model_name="asistenciaregistro",
            name="estado",
            field=models.CharField(
                choices=[
                    ("P", "Presente completo"),
                    ("TM", "Tardía injustificada (media ausencia)"),
                    ("TC", "Tardía injustificada (ausencia completa)"),
                    ("AI", "Ausente injustificada"),
                    ("AJ", "Ausencia justificada"),
                ],
                default="AI",
                max_length=2,
                verbose_name="Estado",
            ),
        ),
        migrations.RunPython(map_tardia_legacy, migrations.RunPython.noop),
    ]
