# Generated by Django 5.2.3 on 2025-07-02 22:58

import django.db.models.deletion
import smart_selects.db_fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('catalogos', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Estudiante',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_estudiante', models.CharField(choices=[('PR', 'Plan regular'), ('PN', 'Plan nacional')], default='PR', max_length=2, verbose_name='Tipo de estudiante')),
                ('identificacion', models.CharField(max_length=20, verbose_name='Identificación')),
                ('primer_apellido', models.CharField(max_length=50, verbose_name='1° Apellido')),
                ('segundo_apellido', models.CharField(blank=True, max_length=50, verbose_name='2° Apellido')),
                ('nombres', models.CharField(max_length=100, verbose_name='Nombre(s)')),
                ('fecha_nacimiento', models.DateField()),
                ('celular', models.CharField(blank=True, max_length=20)),
                ('telefono_casa', models.CharField(blank=True, max_length=20)),
                ('direccion_exacta', models.TextField(blank=True)),
                ('canton', smart_selects.db_fields.ChainedForeignKey(blank=True, chained_field='provincia', chained_model_field='provincia', null=True, on_delete=django.db.models.deletion.PROTECT, to='catalogos.canton')),
                ('distrito', smart_selects.db_fields.ChainedForeignKey(blank=True, chained_field='canton', chained_model_field='canton', null=True, on_delete=django.db.models.deletion.PROTECT, to='catalogos.distrito')),
                ('institucion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.institucion')),
                ('nacionalidad', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='catalogos.nacionalidad')),
                ('provincia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='catalogos.provincia')),
                ('sexo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='catalogos.sexo')),
                ('tipo_identificacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='catalogos.tipoidentificacion')),
            ],
            options={
                'verbose_name': 'Estudiante',
                'verbose_name_plural': 'Estudiantes',
                'ordering': ('primer_apellido', 'nombres'),
            },
        ),
        migrations.CreateModel(
            name='EncargadoEstudiante',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('convivencia', models.BooleanField(default=False, verbose_name='Convive con el estudiante')),
                ('parentesco', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='catalogos.parentesco')),
                ('estudiante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='matricula.estudiante')),
            ],
            options={
                'verbose_name': 'Encargado de estudiante',
                'verbose_name_plural': 'Encargados de estudiantes',
            },
        ),
        migrations.CreateModel(
            name='PersonaContacto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identificacion', models.CharField(max_length=20, verbose_name='Identificación')),
                ('primer_apellido', models.CharField(max_length=50, verbose_name='1° Apellido')),
                ('segundo_apellido', models.CharField(blank=True, max_length=50, verbose_name='2° Apellido')),
                ('nombres', models.CharField(max_length=100, verbose_name='Nombre(s)')),
                ('celular_avisos', models.CharField(blank=True, max_length=20, verbose_name='Celular')),
                ('correo', models.CharField(blank=True, max_length=100, verbose_name='Correo')),
                ('lugar_trabajo', models.CharField(blank=True, max_length=100, verbose_name='Lugar de trabajo')),
                ('telefono_trabajo', models.CharField(blank=True, max_length=20, verbose_name='Teléfono trabajo')),
                ('escolaridad', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='catalogos.escolaridad')),
                ('estado_civil', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='catalogos.estadocivil')),
                ('institucion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.institucion')),
                ('ocupacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='catalogos.ocupacion')),
            ],
            options={
                'verbose_name': 'Persona de contacto',
                'verbose_name_plural': 'Personas de contacto',
                'ordering': ('primer_apellido', 'nombres'),
            },
        ),
        migrations.AddField(
            model_name='estudiante',
            name='contactos',
            field=models.ManyToManyField(related_name='estudiantes', through='matricula.EncargadoEstudiante', to='matricula.personacontacto'),
        ),
        migrations.AddField(
            model_name='encargadoestudiante',
            name='persona_contacto',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='matricula.personacontacto'),
        ),
        migrations.AddConstraint(
            model_name='personacontacto',
            constraint=models.UniqueConstraint(fields=('institucion', 'identificacion'), name='unique_persona_contacto_por_institucion'),
        ),
        migrations.AddConstraint(
            model_name='estudiante',
            constraint=models.UniqueConstraint(fields=('institucion', 'identificacion'), name='unique_estudiante_por_institucion'),
        ),
        migrations.AlterUniqueTogether(
            name='encargadoestudiante',
            unique_together={('estudiante', 'persona_contacto', 'parentesco')},
        ),
    ]
