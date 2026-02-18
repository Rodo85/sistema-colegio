# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalogos', '0004_merge'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='seccion',
            name='tipo_estudiante',
        ),
        migrations.RemoveField(
            model_name='subgrupo',
            name='tipo_estudiante',
        ),
    ]
