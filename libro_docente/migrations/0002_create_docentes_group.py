"""
Migración de datos: crea el grupo "Docentes" con los permisos
necesarios para acceder al Libro del Docente.

Después de aplicar esta migración, para que un docente vea el módulo:
  1. Su usuario debe tener is_staff = True  (puede entrar al admin)
  2. Debe estar asignado al grupo "Docentes"
  3. Debe tener un registro en config_institucional.Profesor ligado a su usuario
  4. Debe tener DocenteAsignacion activas en evaluaciones
"""
from django.db import migrations


def crear_grupo_docentes(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    group, _ = Group.objects.get_or_create(name="Docentes")

    try:
        ct = ContentType.objects.get(app_label="libro_docente", model="asistenciasesion")
        # Permiso custom: acceso al módulo
        for codename in ("access_libro_docente", "view_asistenciasesion"):
            try:
                perm = Permission.objects.get(content_type=ct, codename=codename)
                group.permissions.add(perm)
            except Permission.DoesNotExist:
                pass
        # Permiso view en registro (necesario para que el sidebar muestre el app)
        ct_reg = ContentType.objects.get(app_label="libro_docente", model="asistenciaregistro")
        try:
            perm_reg = Permission.objects.get(content_type=ct_reg, codename="view_asistenciaregistro")
            group.permissions.add(perm_reg)
        except Permission.DoesNotExist:
            pass
    except ContentType.DoesNotExist:
        # Si los ContentTypes no existen aún, re-ejecutar migrate los creará.
        pass


def eliminar_grupo_docentes(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Docentes").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("libro_docente", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(crear_grupo_docentes, eliminar_grupo_docentes),
    ]
