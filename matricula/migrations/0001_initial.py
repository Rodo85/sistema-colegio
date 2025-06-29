# Generated by Django 5.2.3 on 2025-06-22 23:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Adecuacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.CharField(max_length=100, verbose_name='Adecuación')),
            ],
            options={
                'verbose_name': 'Adecuación curricular',
                'verbose_name_plural': 'Adecuaciones',
            },
        ),
        migrations.CreateModel(
            name='Canton',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, verbose_name='Cantón')),
            ],
        ),
        migrations.CreateModel(
            name='Especialidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, verbose_name='Especialidad')),
                ('año', models.PositiveSmallIntegerField(verbose_name='Año')),
            ],
            options={
                'verbose_name': 'Especialidad',
                'verbose_name_plural': 'Especialidades',
            },
        ),
        migrations.CreateModel(
            name='Grupo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nivel', models.CharField(max_length=5, verbose_name='Nivel')),
                ('codigo', models.CharField(max_length=10, verbose_name='Código de grupo')),
            ],
        ),
        migrations.CreateModel(
            name='Nacionalidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, verbose_name='Nacionalidad')),
            ],
            options={
                'verbose_name': 'Nacionalidad',
                'verbose_name_plural': 'Nacionalidades',
            },
        ),
        migrations.CreateModel(
            name='Provincia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, verbose_name='Provincia')),
            ],
        ),
        migrations.CreateModel(
            name='TipoIdentificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, verbose_name='Tipo de identificación')),
            ],
            options={
                'verbose_name': 'Identificación',
                'verbose_name_plural': 'Tipo de Identificación',
            },
        ),
        migrations.CreateModel(
            name='Distrito',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, verbose_name='Distrito')),
                ('canton', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='matricula.canton', verbose_name='Cantón')),
            ],
        ),
        migrations.AddField(
            model_name='canton',
            name='provincia',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='matricula.provincia', verbose_name='Provincia'),
        ),
    ]
