from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_user_fecha_aceptacion_solicitud"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitudregistro",
            name="estado_pago_aprobacion",
            field=models.CharField(
                choices=[("PENDIENTE", "Pago pendiente"), ("AL_DIA", "Al día")],
                default="PENDIENTE",
                help_text="Se aplicará al usuario cuando esta solicitud sea aprobada.",
                max_length=20,
                verbose_name="Estado de pago al aprobar",
            ),
        ),
        migrations.AddField(
            model_name="solicitudregistro",
            name="fecha_limite_pago_aprobacion",
            field=models.DateField(
                blank=True,
                help_text="Opcional. Si se deja vacío y queda en pago pendiente, se asignan 10 días de prueba.",
                null=True,
                verbose_name="Fecha límite de pago al aprobar",
            ),
        ),
    ]
