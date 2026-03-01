from datetime import date

from django.db import migrations, models

import core.models


def set_vencimiento_anual(apps, schema_editor):
    User = apps.get_model("core", "User")
    hoy = date.today()
    vencimiento = date(hoy.year, 12, 20)
    User.objects.all().update(fecha_limite_pago=vencimiento)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_alter_solicitudregistro_comprobante_pago"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="estado_pago",
            field=models.CharField(
                choices=[("PENDIENTE", "Pago pendiente"), ("AL_DIA", "Al día")],
                default="AL_DIA",
                max_length=20,
                verbose_name="Estado de pago",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="fecha_limite_pago",
            field=models.DateField(
                default=core.models.fecha_vencimiento_anual_default,
                help_text="Si llega esta fecha y no se renueva, el acceso se bloquea.",
                verbose_name="Fecha límite de pago",
            ),
        ),
        migrations.RunPython(set_vencimiento_anual, migrations.RunPython.noop),
    ]
