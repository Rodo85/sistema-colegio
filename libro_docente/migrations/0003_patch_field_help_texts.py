import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Sincroniza el estado de la migración con los help_text definidos en los campos
    del modelo AsistenciaSesion. No genera cambios en la BD (solo metadatos).
    """

    dependencies = [
        ("evaluaciones", "0003_fix_trigger_column_name"),
        ("libro_docente", "0002_create_docentes_group"),
    ]

    operations = [
        migrations.AlterField(
            model_name="asistenciasesion",
            name="sesion_numero",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Número de la sesión dentro del día (1, 2, 3…).",
                verbose_name="N.° de sesión",
            ),
        ),
        migrations.AlterField(
            model_name="asistenciasesion",
            name="periodo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="sesiones_asistencia",
                help_text="Período lectivo al que pertenece la sesión (inferido por fecha si no se indica).",
                to="evaluaciones.periodo",
                verbose_name="Período",
            ),
        ),
        # Asegura que los permisos queden registrados en el historial de migraciones
        migrations.AlterModelOptions(
            name="asistenciasesion",
            options={
                "db_table": "asistencia_sesion",
                "ordering": ("fecha", "sesion_numero"),
                "permissions": [("access_libro_docente", "Puede acceder al Libro del Docente")],
                "verbose_name": "Sesión de asistencia",
                "verbose_name_plural": "Sesiones de asistencia",
            },
        ),
        migrations.AlterModelOptions(
            name="asistenciaregistro",
            options={
                "db_table": "asistencia_registro",
                "verbose_name": "Registro de asistencia",
                "verbose_name_plural": "Registros de asistencia",
            },
        ),
    ]
