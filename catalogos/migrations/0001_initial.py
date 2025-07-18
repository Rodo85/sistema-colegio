# Generated by Django 5.2.3 on 2025-07-02 22:58

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
                ('nombre', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Escolaridad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.CharField(max_length=50, unique=True, verbose_name='Escolaridad')),
            ],
            options={
                'verbose_name': 'Escolaridad',
                'verbose_name_plural': 'Escolaridades',
                'ordering': ('descripcion',),
            },
        ),
        migrations.CreateModel(
            name='EstadoCivil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(max_length=30, unique=True, verbose_name='Estado civil')),
            ],
            options={
                'verbose_name': 'Estado civil',
                'verbose_name_plural': 'Estados civiles',
                'ordering': ('estado',),
            },
        ),
        migrations.CreateModel(
            name='Modalidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Modalidad')),
            ],
            options={
                'verbose_name': 'Modalidad',
                'verbose_name_plural': 'Modalidades',
                'ordering': ('nombre',),
            },
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
            name='Nivel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.PositiveSmallIntegerField(unique=True)),
                ('nombre', models.CharField(max_length=20, verbose_name='Nivel')),
            ],
            options={
                'verbose_name': 'Nivel',
                'verbose_name_plural': 'Niveles',
                'ordering': ('numero',),
            },
        ),
        migrations.CreateModel(
            name='Ocupacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.CharField(max_length=50, unique=True, verbose_name='Ocupación')),
            ],
            options={
                'verbose_name': 'Ocupación',
                'verbose_name_plural': 'Ocupaciones',
                'ordering': ('descripcion',),
            },
        ),
        migrations.CreateModel(
            name='Parentesco',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('parentezco', models.CharField(max_length=30, unique=True, verbose_name='Parentesco')),
            ],
            options={
                'verbose_name': 'Parentesco',
                'verbose_name_plural': 'Parentescos',
                'ordering': ('parentezco',),
            },
        ),
        migrations.CreateModel(
            name='Provincia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Sexo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=1, unique=True, verbose_name='Código')),
                ('nombre', models.CharField(max_length=50, verbose_name='Nombre')),
            ],
            options={
                'verbose_name': 'Sexo',
                'verbose_name_plural': 'Sexos',
                'ordering': ('nombre',),
            },
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
                ('nombre', models.CharField(max_length=50)),
                ('canton', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='distritos', to='catalogos.canton')),
            ],
        ),
        migrations.CreateModel(
            name='Especialidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Especialidad')),
                ('modalidad', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='catalogos.modalidad', verbose_name='Modalidad')),
            ],
            options={
                'verbose_name': 'Especialidad',
                'verbose_name_plural': 'Especialidades',
            },
        ),
        migrations.AddField(
            model_name='canton',
            name='provincia',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cantones', to='catalogos.provincia'),
        ),
        migrations.CreateModel(
            name='SubArea',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('especialidad', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='catalogos.especialidad')),
            ],
            options={
                'verbose_name': 'Sub area',
                'verbose_name_plural': 'Subáreas',
                'unique_together': {('especialidad', 'nombre')},
            },
        ),
    ]
