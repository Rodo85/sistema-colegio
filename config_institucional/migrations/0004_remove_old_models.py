# Generated manually to remove old Seccion and Subgrupo models

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('config_institucional', '0003_remove_especialidadcursolectivo_fecha_creacion_and_more'),
    ]

    operations = [
        # Eliminar el modelo Subgrupo primero (porque Clase lo referencia)
        migrations.DeleteModel(
            name='Subgrupo',
        ),
        # Eliminar el modelo Seccion
        migrations.DeleteModel(
            name='Seccion',
        ),
    ]
