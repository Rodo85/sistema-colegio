# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config_institucional', '0003_subgrupocursolectivo_especialidad_curso'),
    ]

    operations = [
        migrations.AddField(
            model_name='seccioncursolectivo',
            name='tipo_estudiante',
            field=models.CharField(
                blank=True,
                choices=[('PR', 'Plan Regular'), ('PN', 'Plan Nacional')],
                help_text='Plan Regular (PR) o Plan Nacional (PN) para estudiantes con discapacidad',
                max_length=2,
                null=True,
                verbose_name='Tipo de estudiante'
            ),
        ),
        migrations.AddField(
            model_name='subgrupocursolectivo',
            name='tipo_estudiante',
            field=models.CharField(
                blank=True,
                choices=[('PR', 'Plan Regular'), ('PN', 'Plan Nacional')],
                help_text='Plan Regular (PR) o Plan Nacional (PN) para estudiantes con discapacidad',
                max_length=2,
                null=True,
                verbose_name='Tipo de estudiante'
            ),
        ),
    ]
