# Asegura que exista el permiso en auth_permission (p. ej. si 0007 se marcó como
# aplicada sin ejecutarse o post_migrate no creó la fila).

from django.db import migrations


PERM_CODENAME = "access_reporte_estudiantes_encargados"
PERM_NAME = "Puede exportar reporte de estudiantes con encargados (Excel)"


def forwards(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ct = ContentType.objects.filter(
        app_label="matricula", model="matriculaacademica"
    ).first()
    if not ct:
        return
    Permission.objects.get_or_create(
        codename=PERM_CODENAME,
        content_type=ct,
        defaults={"name": PERM_NAME},
    )


def backwards(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ct = ContentType.objects.filter(
        app_label="matricula", model="matriculaacademica"
    ).first()
    if not ct:
        return
    Permission.objects.filter(
        content_type=ct, codename=PERM_CODENAME
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("matricula", "0007_matricula_reporte_estudiantes_perm"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
