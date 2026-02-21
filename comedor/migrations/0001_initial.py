from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalogos", "0005_remove_seccion_tipo_estudiante_remove_subgrupo_tipo_estudiante"),
        ("core", "0001_initial"),
        ("matricula", "0004_alter_matriculaacademica_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="BecaComedor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("activa", models.BooleanField(default=True)),
                ("fecha_asignacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                (
                    "curso_lectivo",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="becas_comedor", to="catalogos.cursolectivo"),
                ),
                (
                    "estudiante",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="becas_comedor", to="matricula.estudiante"),
                ),
                (
                    "institucion",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="becas_comedor", to="core.institucion"),
                ),
                (
                    "usuario_asignacion",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="becas_comedor_asignadas", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "usuario_actualizacion",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="becas_comedor_actualizadas", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "verbose_name": "Beca de comedor",
                "verbose_name_plural": "Becas de comedor",
                "ordering": ("estudiante__primer_apellido", "estudiante__nombres"),
                "permissions": [
                    ("access_registro_beca_comedor", "Puede gestionar becas de comedor"),
                    ("access_almuerzo_comedor", "Puede registrar almuerzo en comedor"),
                    ("access_reportes_comedor", "Puede acceder a reportes de comedor"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("institucion", "curso_lectivo", "estudiante"), name="uniq_beca_comedor_por_estudiante_anio_institucion")
                ],
            },
        ),
        migrations.CreateModel(
            name="RegistroAlmuerzo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateField(db_index=True, default=django.utils.timezone.localdate)),
                ("fecha_hora", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("observacion", models.CharField(blank=True, max_length=250)),
                (
                    "curso_lectivo",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="registros_almuerzo", to="catalogos.cursolectivo"),
                ),
                (
                    "estudiante",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="registros_almuerzo", to="matricula.estudiante"),
                ),
                (
                    "institucion",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="registros_almuerzo", to="core.institucion"),
                ),
                (
                    "usuario_registro",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="almuerzos_registrados", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "verbose_name": "Registro de almuerzo",
                "verbose_name_plural": "Registros de almuerzo",
                "ordering": ("-fecha_hora",),
                "indexes": [models.Index(fields=["institucion", "curso_lectivo", "fecha"], name="comedor_reg_institu_818b72_idx")],
                "constraints": [
                    models.UniqueConstraint(fields=("institucion", "curso_lectivo", "estudiante", "fecha"), name="uniq_almuerzo_diario_por_estudiante")
                ],
            },
        ),
    ]

