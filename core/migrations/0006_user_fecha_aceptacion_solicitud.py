from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_user_estado_pago_y_vencimiento"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="fecha_aceptacion_solicitud",
            field=models.DateField(
                blank=True,
                help_text="Fecha en que el superadmin aprobó el acceso del usuario.",
                null=True,
                verbose_name="Fecha de aceptación de solicitud",
            ),
        ),
    ]
