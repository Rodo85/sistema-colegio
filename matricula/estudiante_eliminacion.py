"""
Eliminación definitiva de estudiantes "basura": quita filas PROTECT y luego el Estudiante.
EncargadoEstudiante se elimina en CASCADE al borrar el estudiante.

Tras borrar estudiantes, elimina PersonaContacto (encargado) solo si ya no tiene ningún
EncargadoEstudiante con otro estudiante en el sistema.
"""
from django.db import transaction

from comedor.models import BecaComedor, RegistroAlmuerzo
from libro_docente.models import (
    AsistenciaRegistro,
    EstudianteAdecuacionAsignacion,
    EstudianteAdecuacionNoSignificativaAsignacion,
    EstudianteOcultoAsignacion,
    ListaEstudiantesDocenteItem,
    ObservacionActividadEstudiante,
    PuntajeIndicador,
    PuntajeSimple,
)
from matricula.models import (
    EncargadoEstudiante,
    Estudiante,
    EstudianteInstitucion,
    MatriculaAcademica,
    PersonaContacto,
)


def queryset_activos_sin_matricula_curso(institucion_id, curso_lectivo_id):
    """Misma lógica que el reporte: activos en la institución sin matrícula activa en el curso."""
    estudiantes_activos = Estudiante.objects.filter(
        instituciones_estudiante__institucion_id=institucion_id,
        instituciones_estudiante__estado=EstudianteInstitucion.ACTIVO,
    ).distinct()
    return estudiantes_activos.exclude(
        matriculas_academicas__curso_lectivo_id=curso_lectivo_id,
        matriculas_academicas__estado__iexact="activo",
    )


def queryset_eliminables_basura(institucion_id, curso_lectivo_id):
    """
    Estudiantes que además no tienen ninguna matrícula ACADÉMICA activa en ningún curso lectivo.
    Evita borrar a quien sigue matriculado en otro año.
    """
    base = queryset_activos_sin_matricula_curso(institucion_id, curso_lectivo_id)
    con_matricula_activa = MatriculaAcademica.objects.filter(
        estado__iexact="activo"
    ).values_list("estudiante_id", flat=True)
    return base.exclude(pk__in=con_matricula_activa)


@transaction.atomic
def eliminar_estudiantes_definitivo(estudiante_ids):
    """
    Elimina estudiantes por ID. Debe llamarse solo con IDs ya validados.

    Retorna (cantidad_estudiantes_borrados, cantidad_personas_contacto_borradas).
    Las personas de contacto solo se borran si, tras eliminar encargados por CASCADE,
    no queda ningún EncargadoEstudiante apuntando a esa persona.
    """
    ids = [int(x) for x in estudiante_ids if str(x).strip().isdigit()]
    if not ids:
        return 0, 0
    ids = list(dict.fromkeys(ids))

    persona_ids_afectados = {
        x
        for x in EncargadoEstudiante.objects.filter(estudiante_id__in=ids).values_list(
            "persona_contacto_id", flat=True
        )
        if x
    }

    # Modelos con PROTECT hacia Estudiante primero; luego matrícula/historial; al final Estudiante.
    AsistenciaRegistro.objects.filter(estudiante_id__in=ids).delete()
    PuntajeIndicador.objects.filter(estudiante_id__in=ids).delete()
    ObservacionActividadEstudiante.objects.filter(estudiante_id__in=ids).delete()
    PuntajeSimple.objects.filter(estudiante_id__in=ids).delete()
    EstudianteOcultoAsignacion.objects.filter(estudiante_id__in=ids).delete()
    EstudianteAdecuacionAsignacion.objects.filter(estudiante_id__in=ids).delete()
    EstudianteAdecuacionNoSignificativaAsignacion.objects.filter(
        estudiante_id__in=ids
    ).delete()
    ListaEstudiantesDocenteItem.objects.filter(estudiante_id__in=ids).delete()
    BecaComedor.objects.filter(estudiante_id__in=ids).delete()
    RegistroAlmuerzo.objects.filter(estudiante_id__in=ids).delete()
    MatriculaAcademica.objects.filter(estudiante_id__in=ids).delete()
    EstudianteInstitucion.objects.filter(estudiante_id__in=ids).delete()
    qs_est = Estudiante.objects.filter(pk__in=ids)
    n = qs_est.count()
    qs_est.delete()
    # EncargadoEstudiante ya se eliminó en CASCADE; limpiar PersonaContacto huérfanas.
    n_pc = 0
    for pc_id in persona_ids_afectados:
        if not EncargadoEstudiante.objects.filter(persona_contacto_id=pc_id).exists():
            n_pc += PersonaContacto.objects.filter(pk=pc_id).delete()[0]
    return n, n_pc
