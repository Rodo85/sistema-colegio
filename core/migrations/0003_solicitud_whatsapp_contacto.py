from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_autoregistro_y_matricula_activa"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitudregistro",
            name="telefono_whatsapp",
            field=models.CharField(
                default="",
                help_text="Número de contacto por WhatsApp para verificación.",
                max_length=30,
                verbose_name="WhatsApp de contacto",
            ),
            preserve_default=False,
        ),
    ]
