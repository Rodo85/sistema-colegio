from django.db import migrations, models
from django.db.models import Count


def _normalize_estado(estado):
    if estado == "T":
        return "TM"
    if estado in {"P", "TM", "TC", "AI", "AJ"}:
        return estado
    return "P"


def _severity(estado):
    estado = _normalize_estado(estado)
    if estado in {"AI", "TC"}:
        return 3
    if estado == "TM":
        return 2
    if estado == "AJ":
        return 1
    return 0


def consolidar_sesiones_por_fecha(apps, schema_editor):
    AsistenciaSesion = apps.get_model("libro_docente", "AsistenciaSesion")
    AsistenciaRegistro = apps.get_model("libro_docente", "AsistenciaRegistro")

    duplicados = (
        AsistenciaSesion.objects
        .values("docente_asignacion_id", "fecha")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )

    for dup in duplicados:
        sesiones = list(
            AsistenciaSesion.objects.filter(
                docente_asignacion_id=dup["docente_asignacion_id"],
                fecha=dup["fecha"],
            ).order_by("sesion_numero", "created_at", "id")
        )
        if not sesiones:
            continue

        primaria = min(
            sesiones,
            key=lambda s: (
                0 if (s.sesion_numero or 0) == 1 else 1,
                s.created_at,
                s.id,
            ),
        )
        lecciones_total = 0
        for s in sesiones:
            lecciones_total += (s.lecciones or 1)

        primaria.sesion_numero = 1
        primaria.lecciones = max(1, lecciones_total)
        primaria.save(update_fields=["sesion_numero", "lecciones", "updated_at"])

        primaria_regs = {
            r.estudiante_id: r
            for r in AsistenciaRegistro.objects.filter(sesion_id=primaria.id).order_by("id")
        }

        for extra in sesiones:
            if extra.id == primaria.id:
                continue

            for reg in AsistenciaRegistro.objects.filter(sesion_id=extra.id).order_by("id"):
                nuevo_estado = _normalize_estado(reg.estado)
                actual = primaria_regs.get(reg.estudiante_id)

                if actual is None:
                    reg.sesion_id = primaria.id
                    reg.estado = nuevo_estado
                    reg.save(update_fields=["sesion", "estado", "updated_at"])
                    primaria_regs[reg.estudiante_id] = reg
                    continue

                actual_estado = _normalize_estado(actual.estado)
                if _severity(nuevo_estado) > _severity(actual_estado):
                    actual.estado = nuevo_estado
                if reg.observacion and not (actual.observacion or ""):
                    actual.observacion = reg.observacion[:255]
                actual.save(update_fields=["estado", "observacion", "updated_at"])

            extra.delete()

    AsistenciaRegistro.objects.filter(estado="T").update(estado="TM")
    AsistenciaSesion.objects.exclude(sesion_numero=1).update(sesion_numero=1)
    AsistenciaSesion.objects.filter(lecciones__isnull=True).update(lecciones=1)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("libro_docente", "0011_asistencia_lecciones_y_tardias"),
    ]

    operations = [
        migrations.RunPython(consolidar_sesiones_por_fecha, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="asistenciasesion",
            name="uniq_sesion_asistencia",
        ),
        migrations.AddConstraint(
            model_name="asistenciasesion",
            constraint=models.CheckConstraint(
                check=models.Q(sesion_numero=1),
                name="asis_sesion_numero_unico_dia",
            ),
        ),
        migrations.AddConstraint(
            model_name="asistenciasesion",
            constraint=models.UniqueConstraint(
                fields=("docente_asignacion", "fecha"),
                name="uniq_sesion_asistencia_por_fecha",
            ),
        ),
    ]
