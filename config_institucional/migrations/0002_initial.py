# Generated by Django 5.2.3 on 2025-07-02 22:58

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('catalogos', '0001_initial'),
        ('config_institucional', '0001_initial'),
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='clase',
            name='institucion',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.institucion'),
        ),
        migrations.AddField(
            model_name='clase',
            name='subarea',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='catalogos.subarea', verbose_name='Subárea'),
        ),
        migrations.AddField(
            model_name='nivelinstitucion',
            name='institucion',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.institucion', verbose_name='Institución'),
        ),
        migrations.AddField(
            model_name='nivelinstitucion',
            name='nivel',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='catalogos.nivel', verbose_name='Nivel'),
        ),
        migrations.AddField(
            model_name='profesor',
            name='institucion',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.institucion', verbose_name='Institución'),
        ),
        migrations.AddField(
            model_name='profesor',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='Usuario'),
        ),
        migrations.AddField(
            model_name='clase',
            name='profesor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='config_institucional.profesor', verbose_name='Profesor'),
        ),
        migrations.AddField(
            model_name='seccion',
            name='institucion',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.institucion', verbose_name='Institución'),
        ),
        migrations.AddField(
            model_name='seccion',
            name='nivel',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='catalogos.nivel', verbose_name='Nivel'),
        ),
        migrations.AddField(
            model_name='subgrupo',
            name='institucion',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.institucion', verbose_name='Institución'),
        ),
        migrations.AddField(
            model_name='subgrupo',
            name='seccion',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subgrupos', to='config_institucional.seccion', verbose_name='Sección'),
        ),
        migrations.AddField(
            model_name='clase',
            name='subgrupo',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='config_institucional.subgrupo'),
        ),
        migrations.AlterUniqueTogether(
            name='nivelinstitucion',
            unique_together={('institucion', 'nivel')},
        ),
        migrations.AlterUniqueTogether(
            name='seccion',
            unique_together={('nivel', 'numero')},
        ),
        migrations.AlterUniqueTogether(
            name='subgrupo',
            unique_together={('seccion', 'letra')},
        ),
        migrations.AlterUniqueTogether(
            name='clase',
            unique_together={('subarea', 'subgrupo', 'periodo')},
        ),
    ]
