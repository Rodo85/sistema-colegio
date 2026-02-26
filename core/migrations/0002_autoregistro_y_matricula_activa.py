from datetime import timedelta

from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


def crear_institucion_general(apps, schema_editor):
    Institucion = apps.get_model("core", "Institucion")
    hoy = timezone.now().date()
    correo_base = "INSTITUCION.GENERAL@COLESMART.LOCAL"
    correo = correo_base
    n = 1
    while Institucion.objects.filter(correo=correo).exclude(es_institucion_general=True).exists():
        correo = f"INSTITUCION.GENERAL+{n}@COLESMART.LOCAL"
        n += 1
    defaults = {
        "correo": correo,
        "telefono": "",
        "direccion": "N/A",
        "tipo": "A",
        "fecha_inicio": hoy,
        "fecha_fin": hoy + timedelta(days=3650),
        "matricula_activa": False,
        "es_institucion_general": True,
        "max_asignaciones_general": 10,
    }

    existente = Institucion.objects.filter(es_institucion_general=True).first()
    if existente:
        update_fields = []
        if existente.matricula_activa:
            existente.matricula_activa = False
            update_fields.append("matricula_activa")
        if existente.max_asignaciones_general <= 0:
            existente.max_asignaciones_general = 10
            update_fields.append("max_asignaciones_general")
        if update_fields:
            existente.save(update_fields=update_fields)
        return

    Institucion.objects.get_or_create(
        nombre="INSTITUCION GENERAL",
        defaults=defaults,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="institucion",
            name="es_institucion_general",
            field=models.BooleanField(
                default=False,
                help_text="Marca la institución genérica para docentes sin matrícula activa.",
                verbose_name="Es institución general",
            ),
        ),
        migrations.AddField(
            model_name="institucion",
            name="matricula_activa",
            field=models.BooleanField(
                default=True,
                help_text="Determina si la institución trabaja con listas reales de matrícula.",
                verbose_name="Matrícula activa",
            ),
        ),
        migrations.AddField(
            model_name="institucion",
            name="max_asignaciones_general",
            field=models.PositiveSmallIntegerField(
                default=10,
                help_text="Límite por defecto aplicado a docentes de la Institución General.",
                verbose_name="Máximo de asignaciones (Institución General)",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="estado_solicitud",
            field=models.CharField(
                choices=[("PENDIENTE", "Pendiente"), ("ACTIVA", "Activa"), ("RECHAZADA", "Rechazada")],
                default="ACTIVA",
                max_length=20,
                verbose_name="Estado de solicitud",
            ),
        ),
        migrations.CreateModel(
            name="SolicitudRegistro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("mensaje", models.TextField(blank=True, verbose_name="Mensaje del solicitante")),
                ("comprobante_pago", models.ImageField(upload_to="solicitudes/comprobantes/", verbose_name="Comprobante de pago")),
                (
                    "estado",
                    models.CharField(
                        choices=[("PENDIENTE", "Pendiente"), ("APROBADA", "Aprobada"), ("RECHAZADA", "Rechazada")],
                        default="PENDIENTE",
                        max_length=20,
                        verbose_name="Estado",
                    ),
                ),
                ("motivo_revision", models.TextField(blank=True, verbose_name="Motivo de revisión/rechazo")),
                ("fecha_solicitud", models.DateTimeField(auto_now_add=True)),
                ("fecha_revision", models.DateTimeField(blank=True, null=True)),
                (
                    "institucion_solicitada",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="solicitudes_registro",
                        to="core.institucion",
                    ),
                ),
                (
                    "revisado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="solicitudes_revisadas",
                        to="core.user",
                    ),
                ),
                (
                    "usuario",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="solicitud_registro",
                        to="core.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "Solicitud de registro",
                "verbose_name_plural": "Solicitudes de registro",
                "ordering": ("-fecha_solicitud",),
            },
        ),
        migrations.RunPython(crear_institucion_general, migrations.RunPython.noop),
    ]
