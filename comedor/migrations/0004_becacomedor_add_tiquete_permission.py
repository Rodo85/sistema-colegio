from django.db import migrations


class Migration(migrations.Migration):
    """
    Registra el permiso access_tiquetes_comedor en BecaComedor.Meta.permissions.
    """

    dependencies = [
        ("comedor", "0003_tiquete_registroalmuerzo_cleanup"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="becacomedor",
            options={
                "ordering": ("estudiante__primer_apellido", "estudiante__nombres"),
                "permissions": [
                    ("access_registro_beca_comedor", "Puede gestionar becas de comedor"),
                    ("access_almuerzo_comedor", "Puede registrar almuerzo en comedor"),
                    ("access_reportes_comedor", "Puede acceder a reportes de comedor"),
                    ("access_tiquetes_comedor", "Puede gestionar tiquetes de comedor"),
                ],
                "verbose_name": "Beca de comedor",
                "verbose_name_plural": "Becas de comedor",
            },
        ),
    ]
