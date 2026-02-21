from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("comedor", "0001_initial"),
        ("core", "0001_initial"),
    ]

    operations = [
        # Eliminar unique constraint de fecha para permitir múltiples registros por día
        migrations.RemoveConstraint(
            model_name="registroalmuerzo",
            name="uniq_almuerzo_diario_por_estudiante",
        ),
        # Agregar índice para consultas de intervalo por estudiante
        migrations.AddIndex(
            model_name="registroalmuerzo",
            index=models.Index(
                fields=["institucion", "curso_lectivo", "estudiante", "fecha_hora"],
                name="comedor_reg_institu_est_fh_idx",
            ),
        ),
        # Crear ConfiguracionComedor
        migrations.CreateModel(
            name="ConfiguracionComedor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "intervalo_minutos",
                    models.PositiveIntegerField(
                        default=1200,
                        verbose_name="Intervalo mínimo entre registros (minutos)",
                        help_text=(
                            "Tiempo mínimo en minutos que debe pasar entre dos registros del mismo estudiante. "
                            "Ejemplo: 120 = puede registrar desayuno y almuerzo. 1200 = prácticamente una vez al día."
                        ),
                    ),
                ),
                (
                    "institucion",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="configuracion_comedor",
                        to="core.institucion",
                        verbose_name="Institución",
                    ),
                ),
            ],
            options={
                "verbose_name": "Configuración de comedor",
                "verbose_name_plural": "Configuraciones de comedor",
            },
        ),
    ]
