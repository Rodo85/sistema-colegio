import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("comedor", "0002_configuracion_comedor_remove_constraint"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ----- limpiar RegistroAlmuerzo: quitar observacion y usuario_registro -----
        migrations.RemoveField(
            model_name="registroalmuerzo",
            name="observacion",
        ),
        migrations.RemoveField(
            model_name="registroalmuerzo",
            name="usuario_registro",
        ),
        # ----- TiqueteComedor -----
        migrations.CreateModel(
            name="TiqueteComedor",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "codigo",
                    models.CharField(
                        editable=False,
                        max_length=20,
                        unique=True,
                        verbose_name="Código",
                    ),
                ),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("ALUMNO_TIQ", "Alumno con tiquete"),
                            ("PROFESOR", "Profesor"),
                        ],
                        max_length=15,
                        verbose_name="Tipo",
                    ),
                ),
                (
                    "monto",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=10,
                        verbose_name="Monto (₡)",
                    ),
                ),
                (
                    "activo",
                    models.BooleanField(default=True, verbose_name="Activo"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Fecha de creación"
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tiquetes_comedor_creados",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Creado por",
                    ),
                ),
                (
                    "institucion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tiquetes_comedor",
                        to="core.institucion",
                        verbose_name="Institución",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tiquete de comedor",
                "verbose_name_plural": "Tiquetes de comedor",
                "ordering": ("tipo", "codigo"),
            },
        ),
        # ----- RegistroAlmuerzoTiquete -----
        migrations.CreateModel(
            name="RegistroAlmuerzoTiquete",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "fecha",
                    models.DateField(
                        db_index=True, default=django.utils.timezone.localdate
                    ),
                ),
                (
                    "fecha_hora",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                (
                    "curso_lectivo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registros_almuerzo_tiquete",
                        to="catalogos.cursolectivo",
                        verbose_name="Curso lectivo",
                    ),
                ),
                (
                    "institucion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registros_almuerzo_tiquete",
                        to="core.institucion",
                        verbose_name="Institución",
                    ),
                ),
                (
                    "tiquete",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registros_almuerzo",
                        to="comedor.tiquetecomedor",
                        verbose_name="Tiquete",
                    ),
                ),
            ],
            options={
                "verbose_name": "Registro de almuerzo (tiquete)",
                "verbose_name_plural": "Registros de almuerzo (tiquetes)",
                "ordering": ("-fecha_hora",),
            },
        ),
        migrations.AddIndex(
            model_name="registroalmuerzoTiquete",
            index=models.Index(
                fields=["institucion", "curso_lectivo", "fecha"],
                name="comedor_rat_institu_fecha_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="registroalmuerzoTiquete",
            index=models.Index(
                fields=["tiquete", "fecha_hora"],
                name="comedor_rat_tiquete_fh_idx",
            ),
        ),
    ]
