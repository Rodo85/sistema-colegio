# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('config_institucional', '0004_seccioncursolectivo_tipo_estudiante_subgrupocursolectivo_tipo_estudiante'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subgrupocursolectivo',
            name='tipo_estudiante',
        ),
    ]
