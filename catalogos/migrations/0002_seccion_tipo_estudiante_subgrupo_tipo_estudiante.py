# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='seccion',
            name='tipo_estudiante',
            field=models.CharField(
                blank=True,
                choices=[('PR', 'Plan Regular'), ('PN', 'Plan Nacional')],
                help_text='Indica si la sección es para Plan Regular (PR) o Plan Nacional (PN)',
                max_length=2,
                null=True,
                verbose_name='Tipo de estudiante'
            ),
        ),
        migrations.AddField(
            model_name='subgrupo',
            name='tipo_estudiante',
            field=models.CharField(
                blank=True,
                choices=[('PR', 'Plan Regular'), ('PN', 'Plan Nacional')],
                help_text='Indica si el subgrupo es para Plan Regular (PR) o Plan Nacional (PN)',
                max_length=2,
                null=True,
                verbose_name='Tipo de estudiante'
            ),
        ),
    ]
