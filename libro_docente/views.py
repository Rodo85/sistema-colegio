from datetime import date
from decimal import Decimal
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from evaluaciones.models import (
    DocenteAsignacion,
    EsquemaEvalComponente,
    Periodo,
    PeriodoCursoLectivo,
)
from config_institucional.models import Profesor
from matricula.models import MatriculaAcademica

from .forms import ActividadEvaluacionForm, IndicadorActividadFormSet
from .models import ActividadEvaluacion, AsistenciaRegistro, AsistenciaSesion
from .models import PuntajeIndicador
from .models import ObservacionActividadEstudiante
from .models import PuntajeSimple
from .models import EstudianteOcultoAsignacion
from .models import EstudianteAdecuacionAsignacion
from .services import (
    actividad_pertenece_a_institucion,
    calcular_resumen_evaluacion_completo,
    calcular_resumen_componente_estudiante,
    calcular_total_maximo_actividad,
    copiar_actividad_a_asignaciones,
    duplicar_actividad,
    guardar_puntajes_masivo,
    obtener_porcentaje_componente_esquema,
    porcentaje_disponible_para_tipo,
    puede_usuario_editar_actividad,
)

try:
    import openpyxl
except Exception:
    openpyxl = None

# ─── Tabla: % ausencias injustificadas → asignación final (0-5) ──────────────
# Rangos: [min_inclusive, max_exclusive) → asignación
# 0% a <10% => 5, 10% a <20% => 4, 20% a <30% => 3, 30% a <40% => 2,
# 40% a <50% => 1, 50% o más => 0
_MEP_RANGES = [
    (0, 10, 5),
    (10, 20, 4),
    (20, 30, 3),
    (30, 40, 2),
    (40, 50, 1),
    (50, 100.01, 0),  # >= 50%
]

TIPOS_EVALUACION = (
    ActividadEvaluacion.TAREA,
    ActividadEvaluacion.COTIDIANO,
    ActividadEvaluacion.PRUEBA,
    ActividadEvaluacion.PROYECTO,
)


def _nota_mep(pct: float) -> int:
    """Convierte % ausencias injustificadas a asignación final 0-5."""
    pct = round(pct, 4)
    for min_pct, max_pct, nota in _MEP_RANGES:
        if min_pct <= pct < max_pct:
            return nota
    return 0


def _get_profesor(request):
    """Devuelve el primer Profesor del usuario según la institución activa."""
    qs = Profesor.objects.filter(usuario=request.user).select_related("usuario")
    inst_id = getattr(request, "institucion_activa_id", None)
    if inst_id:
        qs = qs.filter(institucion_id=inst_id)
    return qs.first()


def _get_estudiantes(asignacion):
    """
    Devuelve MatriculaAcademica activas del grupo de la asignación,
    ordenadas por apellido.

    Regla: si hay subgrupo_id (materia técnica o asignación por subgrupo),
    filtrar SOLO por subgrupo. Si solo hay seccion_id (materia académica),
    filtrar por sección completa. Nunca mezclar 9-1A y 9-1B cuando
    la asignación es a un subgrupo específico.
    """
    filtros = {"curso_lectivo": asignacion.curso_lectivo, "estado": "activo"}
    if asignacion.subgrupo_id:
        filtros["subgrupo_id"] = asignacion.subgrupo_id
    elif asignacion.seccion_id:
        filtros["seccion_id"] = asignacion.seccion_id
    else:
        return MatriculaAcademica.objects.none()
    ocultos_ids = list(
        EstudianteOcultoAsignacion.objects.filter(docente_asignacion=asignacion).values_list(
            "estudiante_id", flat=True
        )
    )
    qs = MatriculaAcademica.objects.filter(**filtros)
    if ocultos_ids:
        qs = qs.exclude(estudiante_id__in=ocultos_ids)
    return (
        qs.select_related("estudiante")
        .order_by("estudiante__primer_apellido", "estudiante__segundo_apellido", "estudiante__nombres")
    )


def _get_estudiantes_base(asignacion):
    """
    Lista base oficial del grupo/subgrupo sin aplicar ocultos.
    """
    filtros = {"curso_lectivo": asignacion.curso_lectivo, "estado": "activo"}
    if asignacion.subgrupo_id:
        filtros["subgrupo_id"] = asignacion.subgrupo_id
    elif asignacion.seccion_id:
        filtros["seccion_id"] = asignacion.seccion_id
    else:
        return MatriculaAcademica.objects.none()
    return (
        MatriculaAcademica.objects.filter(**filtros)
        .select_related("estudiante")
        .order_by("estudiante__primer_apellido", "estudiante__segundo_apellido", "estudiante__nombres")
    )


def _get_ids_adecuacion(asignacion):
    return set(
        EstudianteAdecuacionAsignacion.objects.filter(docente_asignacion=asignacion).values_list(
            "estudiante_id", flat=True
        )
    )


def _get_estudiantes_para_actividad(asignacion, actividad):
    """
    Filtra estudiantes según alcance de la actividad:
    - GRUPO: excluye estudiantes marcados con adecuación.
    - ADECUACION: muestra solo estudiantes marcados con adecuación.
    """
    qs = _get_estudiantes(asignacion)
    ids_adecuacion = _get_ids_adecuacion(asignacion)
    alcance = actividad.alcance_estudiantes
    if alcance == "GRUPO":
        alcance = ActividadEvaluacion.ALCANCE_REGULARES
    if alcance == ActividadEvaluacion.ALCANCE_TODOS:
        return qs
    if not ids_adecuacion:
        return qs if alcance != ActividadEvaluacion.ALCANCE_ADECUACION else qs.none()
    if alcance == ActividadEvaluacion.ALCANCE_ADECUACION:
        return qs.filter(estudiante_id__in=ids_adecuacion)
    return qs.exclude(estudiante_id__in=ids_adecuacion)


def _tipos_habilitados_por_esquema(asignacion):
    """
    Tipos visibles según componentes del esquema de evaluación snapshot.
    """
    if not asignacion.eval_scheme_snapshot_id:
        return []
    tipos = []
    componentes = (
        EsquemaEvalComponente.objects
        .filter(esquema=asignacion.eval_scheme_snapshot)
        .select_related("componente")
    )
    for c in componentes:
        cod = (c.componente.codigo or "").strip().upper()
        if cod in ("TAR", "TAREAS", "TAREA") and ActividadEvaluacion.TAREA not in tipos:
            tipos.append(ActividadEvaluacion.TAREA)
        elif cod in ("COT", "COTIDIANO") and ActividadEvaluacion.COTIDIANO not in tipos:
            tipos.append(ActividadEvaluacion.COTIDIANO)
        elif cod in ("PRU", "PRUEBA", "PRUEBAS") and ActividadEvaluacion.PRUEBA not in tipos:
            tipos.append(ActividadEvaluacion.PRUEBA)
        elif cod in ("PRO", "PROYECTO", "PROYECTOS") and ActividadEvaluacion.PROYECTO not in tipos:
            tipos.append(ActividadEvaluacion.PROYECTO)
    return tipos


def _infer_periodo(asignacion, fecha):
    """
    Infiere el Periodo a partir de la fecha usando PeriodoCursoLectivo.
    Devuelve el Periodo si hay coincidencia exacta por fechas;
    si no, devuelve el primero activo o None.
    """
    inst_id = asignacion.subarea_curso.institucion_id
    periodos_cl = (
        PeriodoCursoLectivo.objects
        .filter(
            institucion_id=inst_id,
            curso_lectivo=asignacion.curso_lectivo,
            activo=True,
        )
        .select_related("periodo")
        .order_by("periodo__numero")
    )
    for pcl in periodos_cl:
        if pcl.fecha_inicio and pcl.fecha_fin:
            if pcl.fecha_inicio <= fecha <= pcl.fecha_fin:
                return pcl.periodo
    first = periodos_cl.first()
    return first.periodo if first else None


def _calcular_resumen(asignacion, periodo, matriculas):
    """
    Calcula resumen de asistencia por estudiante en un período.
    Regla vigente: el período se calcula por lecciones, no por cantidad
    de sesiones.
    """
    sesiones = AsistenciaSesion.objects.filter(
        docente_asignacion=asignacion,
        periodo=periodo,
    ).order_by("fecha", "sesion_numero")
    sesiones = list(sesiones)
    total_sesiones = len(sesiones)
    sesion_ids = [s.id for s in sesiones]
    matricula_est_ids = [m.estudiante_id for m in matriculas]
    registros_raw = AsistenciaRegistro.objects.filter(
        sesion_id__in=sesion_ids,
        estudiante_id__in=matricula_est_ids,
    )
    registros_map = {
        (r.estudiante_id, r.sesion_id): r
        for r in registros_raw
    }

    # Peso del componente ASISTENCIA en el esquema snapshot.
    # Se busca por código exacto "ASISTENCIA" o "ASIS", y también por
    # nombre que contenga "asistencia" — sin distinción de mayúsculas.
    peso_asistencia = Decimal("0")
    comp_asistencia = None
    if asignacion.eval_scheme_snapshot_id:
        comp_asistencia = (
            EsquemaEvalComponente.objects
            .filter(esquema=asignacion.eval_scheme_snapshot)
            .filter(
                Q(componente__codigo__iregex=r"^asis(tencia)?$") |
                Q(componente__nombre__icontains="asistencia")
            )
            .select_related("componente")
            .first()
        )
        if comp_asistencia:
            peso_asistencia = comp_asistencia.porcentaje

    resultados = []
    estados_validos = {k for k, _ in AsistenciaRegistro.ESTADO_CHOICES}
    for m in matriculas:
        est = m.estudiante
        fecha_ingreso_grupo = m.fecha_asignacion
        sesiones_est = [
            s for s in sesiones
            if (not fecha_ingreso_grupo or s.fecha >= fecha_ingreso_grupo)
        ]
        total_lecciones = sum((s.lecciones or 1) for s in sesiones_est)

        presentes = 0
        tardias_media = 0
        tardias_completa = 0
        ausentes_inj = Decimal("0")
        ausentes_just = 0
        for s in sesiones_est:
            lecciones = Decimal(str(s.lecciones or 1))
            reg = registros_map.get((est.id, s.id))
            if reg is None:
                ausentes_inj += lecciones
                continue
            if reg.lecciones_injustificadas is not None:
                valor_manual = Decimal(reg.lecciones_injustificadas)
                if valor_manual < 0:
                    valor_manual = Decimal("0")
                if valor_manual > lecciones:
                    valor_manual = lecciones
                ausentes_inj += valor_manual
                continue
            estado = reg.estado
            if estado == "T":
                estado = AsistenciaRegistro.TARDIA_MEDIA
            if estado not in estados_validos:
                estado = AsistenciaRegistro.PRESENTE
            if estado == AsistenciaRegistro.PRESENTE:
                presentes += 1
            elif estado == AsistenciaRegistro.TARDIA_MEDIA:
                tardias_media += 1
                ausentes_inj += (lecciones / Decimal("2"))
            elif estado == AsistenciaRegistro.TARDIA_COMPLETA:
                tardias_completa += 1
                ausentes_inj += lecciones
            elif estado == AsistenciaRegistro.AUSENTE_INJUSTIFICADA:
                ausentes_inj += lecciones
            elif estado == AsistenciaRegistro.AUSENTE_JUSTIFICADA:
                ausentes_just += 1

        pct = (float((ausentes_inj / Decimal(str(total_lecciones))) * Decimal("100")) if total_lecciones > 0 else 0.0)
        puntaje_base = _nota_mep(pct)
        # aporte_real = (asignacion_final / 5) * peso_asistencia_esquema
        aporte_real = (
            Decimal(str(puntaje_base)) / Decimal("5") * peso_asistencia
            if peso_asistencia else Decimal("0")
        )

        # Indicador visual
        if total_lecciones == 0:
            nivel_alerta = "nodata"
        elif pct == 0:
            nivel_alerta = "ok"
        elif pct <= 15:
            nivel_alerta = "warning"
        else:
            nivel_alerta = "danger"

        resultados.append({
            "estudiante": est,
            "presentes": presentes,
            "tardias_media": tardias_media,
            "tardias_completa": tardias_completa,
            "ausentes_inj_lecciones": ausentes_inj.quantize(Decimal("0.01")),
            "ausentes_just": ausentes_just,
            "total_lecciones": total_lecciones,
            "pct": round(pct, 2),
            "nota_mep": puntaje_base,
            "peso_asistencia": peso_asistencia,
            "aporte_real": round(aporte_real, 2),
            "nivel_alerta": nivel_alerta,
        })

    nombre_componente = (
        comp_asistencia.componente.nombre if comp_asistencia else "Asistencia"
    )
    resultados.sort(
        key=lambda r: (
            r["estudiante"].primer_apellido or "",
            r["estudiante"].segundo_apellido or "",
            r["estudiante"].nombres or "",
        )
    )
    return {
        "total_sesiones": total_sesiones,
        "total_lecciones_periodo": sum((s.lecciones or 1) for s in sesiones),
        "peso_asistencia": peso_asistencia,
        "tiene_componente": comp_asistencia is not None,
        "nombre_componente": nombre_componente,
        "estudiantes": resultados,
    }


# ═══════════════════════════════════════════════════════════════════════
#  VISTAS
# ═══════════════════════════════════════════════════════════════════════

@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def home_docente(request):
    """Home del docente: tarjetas por cada DocenteAsignacion activa."""
    profesor = _get_profesor(request)
    error = None
    asignaciones_data = []

    if not profesor:
        error = "No tienes perfil de docente registrado en esta institución."
    else:
        componentes_prefetch = Prefetch(
            "eval_scheme_snapshot__componentes_esquema",
            queryset=EsquemaEvalComponente.objects.select_related("componente").order_by("componente__nombre"),
        )
        raw = list(
            DocenteAsignacion.objects
            .filter(docente=profesor, activo=True)
            .select_related(
                "subarea_curso__subarea",
                "curso_lectivo",
                "seccion__nivel",
                "subgrupo__seccion__nivel",
                "eval_scheme_snapshot",
            )
            .prefetch_related(componentes_prefetch)
        )

        def _sort_key(a):
            if a.subgrupo_id:
                n = a.subgrupo.seccion.nivel.numero
                s = a.subgrupo.seccion.numero
                l = (a.subgrupo.letra or "").upper()
                return (n, s, l)
            if a.seccion_id:
                n = a.seccion.nivel.numero
                s = a.seccion.numero
                return (n, s, "")
            return (999, 999, "")

        raw.sort(key=lambda a: (_sort_key(a), a.subarea_curso.subarea.nombre))

        # Sesiones hoy por asignación (1 query para todas)
        asignacion_ids = [a.id for a in raw]
        sesiones_hoy_counts = dict(
            AsistenciaSesion.objects.filter(
                docente_asignacion_id__in=asignacion_ids, fecha=timezone.localdate()
            ).values("docente_asignacion_id").annotate(cnt=Count("id")).values_list("docente_asignacion_id", "cnt")
        )

        hoy = timezone.localdate()
        for a in raw:
            componentes_raw = list(a.eval_scheme_snapshot.componentes_esquema.all()) if a.eval_scheme_snapshot_id else []
            componentes = []
            for c in componentes_raw:
                cod = (c.componente.codigo or "").strip().upper()
                if cod in ("TAR", "TAREAS", "TAREA"):
                    tipo_param = "TAREA"
                elif cod in ("COT", "COTIDIANO"):
                    tipo_param = "COTIDIANO"
                elif cod in ("PRU", "PRUEBA", "PRUEBAS"):
                    tipo_param = "PRUEBA"
                elif cod in ("PRO", "PROYECTO", "PROYECTOS"):
                    tipo_param = "PROYECTO"
                else:
                    tipo_param = None
                componentes.append({
                    "componente": c.componente,
                    "porcentaje": c.porcentaje,
                    "tipo_param": tipo_param,
                })

            tiene_asistencia = any(
                (c["componente"].codigo or "").upper() in ("ASISTENCIA", "ASIS") or
                "ASISTENCIA" in (c["componente"].nombre or "").upper()
                for c in componentes
            )

            sesiones_hoy = sesiones_hoy_counts.get(a.id, 0)

            # Etiqueta del grupo: subgrupo completo (7-1A) o sección (7-1)
            if a.subgrupo_id:
                grupo_label = str(a.subgrupo)  # ej. 7-1A, 8-3B
            elif a.seccion_id:
                grupo_label = str(a.seccion)   # ej. 7-1
            else:
                grupo_label = "—"

            asignaciones_data.append({
                "obj": a,
                "componentes": componentes,
                "tiene_asistencia": tiene_asistencia,
                "sesiones_hoy": sesiones_hoy,
                "grupo_label": grupo_label,
            })

    return render(request, "libro_docente/hoy.html", {
        "asignaciones": asignaciones_data,
        "hoy": timezone.localdate(),
        "profesor": profesor,
        "error": error,
    })


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def estudiantes_config_view(request, asignacion_id):
    """
    Pantalla independiente para gestionar estudiantes ocultos y con adecuación.
    """
    asignacion = _obtener_asignacion_con_permiso(request, asignacion_id)
    if asignacion is None:
        messages.error(request, "No tienes acceso a esta asignación.")
        return redirect("libro_docente:home")

    base = list(_get_estudiantes_base(asignacion))
    base_ids = [m.estudiante_id for m in base]
    ocultos_actuales = set(
        EstudianteOcultoAsignacion.objects.filter(
            docente_asignacion=asignacion,
            estudiante_id__in=base_ids,
        ).values_list("estudiante_id", flat=True)
    )
    adecuacion_actuales = _get_ids_adecuacion(asignacion).intersection(set(base_ids))

    if request.method == "POST":
        oculto_ids = {int(x) for x in request.POST.getlist("oculto_ids") if str(x).isdigit()}
        adecuacion_ids = {int(x) for x in request.POST.getlist("adecuacion_ids") if str(x).isdigit()}
        oculto_ids = oculto_ids.intersection(set(base_ids))
        adecuacion_ids = adecuacion_ids.intersection(set(base_ids))

        with transaction.atomic():
            EstudianteOcultoAsignacion.objects.filter(
                docente_asignacion=asignacion,
                estudiante_id__in=base_ids,
            ).exclude(estudiante_id__in=oculto_ids).delete()
            EstudianteAdecuacionAsignacion.objects.filter(
                docente_asignacion=asignacion,
                estudiante_id__in=base_ids,
            ).exclude(estudiante_id__in=adecuacion_ids).delete()

            for est_id in oculto_ids - ocultos_actuales:
                EstudianteOcultoAsignacion.objects.get_or_create(
                    docente_asignacion=asignacion,
                    estudiante_id=est_id,
                    defaults={"created_by": request.user},
                )
            for est_id in adecuacion_ids - adecuacion_actuales:
                EstudianteAdecuacionAsignacion.objects.get_or_create(
                    docente_asignacion=asignacion,
                    estudiante_id=est_id,
                    defaults={"created_by": request.user},
                )
        messages.success(request, "Configuración de estudiantes guardada.")
        return redirect(reverse("libro_docente:estudiantes_config", args=[asignacion.id]))

    filas = []
    for m in base:
        est = m.estudiante
        filas.append({
            "id": est.id,
            "nombre": str(est),
            "identificacion": est.identificacion,
            "oculto": est.id in ocultos_actuales,
            "adecuacion": est.id in adecuacion_actuales,
        })
    filas.sort(key=lambda x: x["nombre"])
    return render(request, "libro_docente/estudiantes_config.html", {
        "asignacion": asignacion,
        "filas": filas,
    })


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def asistencia_view(request, asignacion_id):
    """
    Pantalla de asistencia diaria: una sola sesión por fecha, con cantidad
    de lecciones del día y marcas rápidas por estudiante.
    """
    profesor = _get_profesor(request)
    if not profesor:
        messages.error(request, "No tienes perfil de docente en esta institución.")
        return redirect("libro_docente:home")

    asignacion = get_object_or_404(
        DocenteAsignacion.objects.select_related(
            "subarea_curso__subarea", "curso_lectivo",
            "seccion__nivel", "subgrupo__seccion__nivel",
        ),
        id=asignacion_id, docente=profesor, activo=True,
    )

    # ── Fecha ────────────────────────────────────────────────────────────
    hoy = timezone.localdate()
    fecha_str = (request.POST if request.method == "POST" else request.GET).get("fecha")
    try:
        fecha = date.fromisoformat(fecha_str) if fecha_str else hoy
    except ValueError:
        fecha = hoy

    # ── Lecciones del día ────────────────────────────────────────────────
    raw_lecciones = (request.POST if request.method == "POST" else request.GET).get("lecciones")
    try:
        lecciones = int(raw_lecciones) if raw_lecciones else 1
    except (TypeError, ValueError):
        lecciones = 1
    lecciones = max(1, lecciones)

    # ── POST: guardar sesión ─────────────────────────────────────────────
    if request.method == "POST":
        periodo = _infer_periodo(asignacion, fecha)
        inst_id = asignacion.subarea_curso.institucion_id

        try:
            with transaction.atomic():
                sesion, _ = AsistenciaSesion.objects.get_or_create(
                    docente_asignacion=asignacion,
                    periodo=periodo,
                    fecha=fecha,
                    sesion_numero=1,
                    defaults={
                        "institucion_id": inst_id,
                        "curso_lectivo": asignacion.curso_lectivo,
                        "lecciones": lecciones,
                        "created_by": request.user,
                    },
                )
                sesion.lecciones = lecciones
                sesion.save(update_fields=["lecciones", "updated_at"])
                matriculas = _get_estudiantes(asignacion)
                bulk_create = []
                bulk_update = []
                existing = {r.estudiante_id: r for r in sesion.registros.all()}

                for m in matriculas:
                    est_id = m.estudiante_id
                    raw_estado = request.POST.get(f"estado_{est_id}", AsistenciaRegistro.PRESENTE)
                    estado = raw_estado if raw_estado in dict(AsistenciaRegistro.ESTADO_CHOICES) else AsistenciaRegistro.PRESENTE
                    obs = request.POST.get(f"obs_{est_id}", "")[:255]
                    raw_lecc_inj = (request.POST.get(f"inj_{est_id}", "") or "").strip().replace(",", ".")
                    lecc_inj = None
                    if raw_lecc_inj != "":
                        try:
                            lecc_inj = Decimal(raw_lecc_inj)
                        except Exception:
                            messages.error(request, f"Lecciones injustificadas inválidas para estudiante ID {est_id}.")
                            return redirect(f"{request.path}?fecha={fecha}&lecciones={lecciones}")
                        if lecc_inj < 0 or lecc_inj > Decimal(str(lecciones)):
                            messages.error(
                                request,
                                f"Lecciones injustificadas fuera de rango para estudiante ID {est_id}. Debe estar entre 0 y {lecciones}.",
                            )
                            return redirect(f"{request.path}?fecha={fecha}&lecciones={lecciones}")
                        if (lecc_inj * 2) != (lecc_inj * 2).to_integral_value():
                            messages.error(
                                request,
                                f"Lecciones injustificadas inválidas para estudiante ID {est_id}. Use pasos de 0.5.",
                            )
                            return redirect(f"{request.path}?fecha={fecha}&lecciones={lecciones}")

                    if est_id in existing:
                        reg = existing[est_id]
                        reg.estado = estado
                        reg.lecciones_injustificadas = lecc_inj
                        reg.observacion = obs
                        bulk_update.append(reg)
                    else:
                        bulk_create.append(
                            AsistenciaRegistro(
                                sesion=sesion,
                                estudiante_id=est_id,
                                estado=estado,
                                lecciones_injustificadas=lecc_inj,
                                observacion=obs,
                            )
                        )

                if bulk_create:
                    AsistenciaRegistro.objects.bulk_create(bulk_create)
                if bulk_update:
                    AsistenciaRegistro.objects.bulk_update(
                        bulk_update,
                        ["estado", "lecciones_injustificadas", "observacion"],
                    )

            messages.success(
                request,
                f"✔ Asistencia del {fecha.strftime('%d/%m/%Y')} guardada ({lecciones} lecciones).",
            )
        except Exception as exc:
            messages.error(request, f"Error al guardar: {exc}")

        return redirect(f"{request.path}?fecha={fecha}&lecciones={lecciones}")

    # ── GET ──────────────────────────────────────────────────────────────
    sesion_actual = (
        AsistenciaSesion.objects
        .filter(docente_asignacion=asignacion, fecha=fecha)
        .order_by("sesion_numero")
        .first()
    )
    if sesion_actual:
        lecciones = sesion_actual.lecciones or 1

    # Estados guardados de la fecha seleccionada
    estados_guardados = {}
    obs_guardadas = {}
    inj_guardadas = {}
    if sesion_actual:
        for reg in sesion_actual.registros.select_related("estudiante"):
            estado = reg.estado
            if estado == "T":
                estado = AsistenciaRegistro.TARDIA_MEDIA
            estados_guardados[reg.estudiante_id] = estado
            obs_guardadas[reg.estudiante_id] = reg.observacion
            inj_guardadas[reg.estudiante_id] = reg.lecciones_injustificadas

    matriculas = _get_estudiantes(asignacion)
    estudiantes = []
    for m in matriculas:
        est = m.estudiante
        estado = estados_guardados.get(est.id, AsistenciaRegistro.PRESENTE)
        estudiantes.append({
            "id": est.id,
            "nombre": str(est),
            "identificacion": est.identificacion,
            "estado": estado,
            "lecciones_injustificadas": inj_guardadas.get(est.id),
            "observacion": obs_guardadas.get(est.id, ""),
        })
    estudiantes.sort(key=lambda e: e["nombre"])

    periodo = _infer_periodo(asignacion, fecha)
    periodos_cl = (
        PeriodoCursoLectivo.objects
        .filter(
            institucion_id=asignacion.subarea_curso.institucion_id,
            curso_lectivo=asignacion.curso_lectivo,
            activo=True,
        )
        .select_related("periodo")
        .order_by("periodo__numero")
    )

    return render(request, "libro_docente/asistencia.html", {
        "asignacion": asignacion,
        "fecha": fecha,
        "hoy": hoy,
        "lecciones": lecciones,
        "sesion_actual": sesion_actual,
        "estudiantes": estudiantes,
        "total_estudiantes": len(estudiantes),
        "periodo": periodo,
        "periodos_cl": periodos_cl,
        "PRESENTE": AsistenciaRegistro.PRESENTE,
        "TARDIA_MEDIA": AsistenciaRegistro.TARDIA_MEDIA,
        "TARDIA_COMPLETA": AsistenciaRegistro.TARDIA_COMPLETA,
        "AI": AsistenciaRegistro.AUSENTE_INJUSTIFICADA,
        "AJ": AsistenciaRegistro.AUSENTE_JUSTIFICADA,
    })


def _obtener_asignacion_con_permiso(request, asignacion_id):
    """
    Devuelve la asignación si el usuario tiene acceso.
    Superadmin: cualquier asignación. Usuario normal: solo sus asignaciones.
    """
    profesor = _get_profesor(request)
    if request.user.is_superuser:
        return get_object_or_404(
            DocenteAsignacion.objects.select_related(
                "subarea_curso__subarea", "curso_lectivo",
                "seccion__nivel", "subgrupo__seccion__nivel",
            ),
            id=asignacion_id, activo=True,
        )
    if not profesor:
        return None
    return get_object_or_404(
        DocenteAsignacion.objects.select_related(
            "subarea_curso__subarea", "curso_lectivo",
            "seccion__nivel", "subgrupo__seccion__nivel",
        ),
        id=asignacion_id, docente=profesor, activo=True,
    )


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def detalle_estudiante_view(request, asignacion_id, estudiante_id):
    """
    Detalle de asistencia de un estudiante en un período.
    Historial de registros + resumen acumulado (reutiliza _calcular_resumen).
    """
    asignacion = _obtener_asignacion_con_permiso(request, asignacion_id)
    if asignacion is None:
        messages.error(request, "No tienes acceso a esta asignación.")
        return redirect("libro_docente:home")

    inst_id = asignacion.subarea_curso.institucion_id
    periodos_cl = list(
        PeriodoCursoLectivo.objects
        .filter(
            institucion_id=inst_id,
            curso_lectivo=asignacion.curso_lectivo,
            activo=True,
        )
        .select_related("periodo")
        .order_by("periodo__numero")
    )

    # Período seleccionado
    try:
        periodo_id = int(request.GET.get("periodo", 0))
    except (ValueError, TypeError):
        periodo_id = 0
    if not periodo_id and periodos_cl:
        p = _infer_periodo(asignacion, timezone.localdate())
        periodo_id = (p.id if p else periodos_cl[0].periodo_id)

    periodo_sel = None
    for pcl in periodos_cl:
        if pcl.periodo_id == periodo_id:
            periodo_sel = pcl.periodo
            break

    # Verificar que el estudiante pertenece al grupo
    matriculas = _get_estudiantes(asignacion)
    matricula_est = matriculas.filter(estudiante_id=estudiante_id).first()
    if not matricula_est:
        messages.error(request, "El estudiante no pertenece a este grupo.")
        url = reverse("libro_docente:resumen", args=[asignacion_id])
        if periodo_id:
            url += f"?periodo={periodo_id}"
        return redirect(url)

    estudiante = matricula_est.estudiante

    # Historial de asistencia (registros del estudiante en el período)
    historial = []
    if periodo_sel:
        sesiones = AsistenciaSesion.objects.filter(
            docente_asignacion=asignacion,
            periodo=periodo_sel,
        ).order_by("fecha", "sesion_numero")
        sesion_ids = list(sesiones.values_list("id", flat=True))
        registros = list(
            AsistenciaRegistro.objects
            .filter(sesion_id__in=sesion_ids, estudiante_id=estudiante_id)
            .select_related("sesion")
            .order_by("sesion__fecha", "sesion__sesion_numero")
        )
        for reg in registros:
            estado = reg.estado
            if estado == "T":
                estado = AsistenciaRegistro.TARDIA_MEDIA
            estado_display = dict(AsistenciaRegistro.ESTADO_CHOICES).get(estado, reg.get_estado_display())
            historial.append({
                "fecha": reg.sesion.fecha,
                "lecciones": reg.sesion.lecciones or 1,
                "estado": estado,
                "estado_display": estado_display,
                "lecciones_injustificadas": reg.lecciones_injustificadas,
                "observacion": reg.observacion or "",
            })
        # Sesiones sin registro (cuentan como AI)
        sesiones_data = {s.id: (s.fecha, s.lecciones or 1) for s in sesiones}
        registradas_sesion_ids = {r.sesion_id for r in registros}
        for sid, (f, lecciones) in sesiones_data.items():
            if sid not in registradas_sesion_ids:
                historial.append({
                    "fecha": f,
                    "lecciones": lecciones,
                    "estado": AsistenciaRegistro.AUSENTE_INJUSTIFICADA,
                    "estado_display": "Ausente injustificada",
                    "lecciones_injustificadas": lecciones,
                    "observacion": "(sin registro)",
                })
        historial.sort(key=lambda x: x["fecha"])

    # Resumen acumulado (reutilizar _calcular_resumen para un solo estudiante)
    resumen_est = None
    nombre_componente = "Asistencia"
    if periodo_sel:
        resumen = _calcular_resumen(asignacion, periodo_sel, [matricula_est])
        nombre_componente = resumen.get("nombre_componente", "Asistencia")
        for r in resumen["estudiantes"]:
            if r["estudiante"].id == estudiante_id:
                resumen_est = r
                break

    return render(request, "libro_docente/detalle_estudiante.html", {
        "asignacion": asignacion,
        "estudiante": estudiante,
        "periodos_cl": periodos_cl,
        "periodo_id": periodo_id,
        "periodo_sel": periodo_sel,
        "historial": historial,
        "resumen": resumen_est,
        "nombre_componente": nombre_componente,
        "ESTADO_CHOICES": dict(AsistenciaRegistro.ESTADO_CHOICES),
    })


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def resumen_view(request, asignacion_id):
    """Resumen de asistencia por período para una asignación."""
    profesor = _get_profesor(request)
    if not profesor:
        messages.error(request, "No tienes perfil de docente en esta institución.")
        return redirect("libro_docente:home")

    asignacion = get_object_or_404(
        DocenteAsignacion.objects.select_related(
            "subarea_curso__subarea", "curso_lectivo",
            "seccion__nivel", "subgrupo__seccion__nivel",
        ),
        id=asignacion_id, docente=profesor, activo=True,
    )

    inst_id = asignacion.subarea_curso.institucion_id
    periodos_cl = list(
        PeriodoCursoLectivo.objects
        .filter(
            institucion_id=inst_id,
            curso_lectivo=asignacion.curso_lectivo,
            activo=True,
        )
        .select_related("periodo")
        .order_by("periodo__numero")
    )

    # Período seleccionado
    try:
        periodo_id = int(request.GET.get("periodo", 0))
    except (ValueError, TypeError):
        periodo_id = 0

    if not periodo_id:
        p = _infer_periodo(asignacion, timezone.localdate())
        if p:
            periodo_id = p.id
        elif periodos_cl:
            periodo_id = periodos_cl[0].periodo_id

    periodo_sel = None
    for pcl in periodos_cl:
        if pcl.periodo_id == periodo_id:
            periodo_sel = pcl.periodo
            break

    resumen = {
        "total_sesiones": 0,
        "total_lecciones_periodo": 0,
        "peso_asistencia": Decimal("0"),
        "tiene_componente": False,
        "estudiantes": [],
    }
    if periodo_sel:
        matriculas = _get_estudiantes(asignacion)
        resumen = _calcular_resumen(asignacion, periodo_sel, matriculas)

    return render(request, "libro_docente/resumen.html", {
        "asignacion": asignacion,
        "periodos_cl": periodos_cl,
        "periodo_id": periodo_id,
        "periodo_sel": periodo_sel,
        "resumen": resumen,
    })


# ═══════════════════════════════════════════════════════════════════════════
#  EVALUACIÓN POR INDICADORES (TAREAS / COTIDIANOS)
# ═══════════════════════════════════════════════════════════════════════════


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def actividad_list_view(request, asignacion_id):
    """
    Lista actividades de evaluación de una asignación.
    Filtra por periodo y tipo_componente (opcionales por GET).
    """
    asignacion = _obtener_asignacion_con_permiso(request, asignacion_id)
    if asignacion is None:
        messages.error(request, "No tienes acceso a esta asignación.")
        return redirect("libro_docente:home")

    inst_id = asignacion.subarea_curso.institucion_id
    inst_activa = getattr(request, "institucion_activa_id", None)
    if inst_activa and inst_id != inst_activa:
        messages.error(request, "No puedes acceder a actividades de otra institución.")
        return redirect("libro_docente:home")

    periodos_cl = list(
        PeriodoCursoLectivo.objects
        .filter(institucion_id=inst_id, curso_lectivo=asignacion.curso_lectivo, activo=True)
        .select_related("periodo")
        .order_by("periodo__numero")
    )

    available_tipos = _tipos_habilitados_por_esquema(asignacion)
    if not available_tipos:
        available_tipos = [ActividadEvaluacion.TAREA, ActividadEvaluacion.COTIDIANO]

    periodo_id_raw = request.GET.get("periodo")
    periodo_id = int(periodo_id_raw) if periodo_id_raw and str(periodo_id_raw).isdigit() else None
    tipo = request.GET.get("tipo", "").upper()
    orden = request.GET.get("orden", "fecha")

    if tipo not in available_tipos:
        tipo = available_tipos[0]

    if tipo in available_tipos and not periodo_id and periodos_cl:
        first_pcl = periodos_cl[0]
        return redirect(
            reverse("libro_docente:actividad_list", args=[asignacion_id])
            + f"?periodo={first_pcl.periodo_id}&tipo={tipo}"
        )

    qs = ActividadEvaluacion.objects.filter(
        docente_asignacion=asignacion,
        institucion_id=inst_id,
    ).select_related("periodo").prefetch_related("indicadores")

    if periodo_id:
        qs = qs.filter(periodo_id=periodo_id)
    qs = qs.filter(tipo_componente=tipo)

    if orden == "titulo":
        qs = qs.order_by("titulo")
    elif orden == "estado":
        qs = qs.order_by("estado", "-created_at")
    elif orden == "tipo":
        qs = qs.order_by("tipo_componente", "-created_at")
    else:
        qs = qs.order_by("-created_at")

    actividades_raw = list(qs)
    actividades = []
    for a in actividades_raw:
        es_simple = a.tipo_componente in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO)
        if es_simple:
            total_max = a.puntaje_total or 0
            total_ind = 1 if total_max else 0
        else:
            indicadores_activos = [i for i in a.indicadores.all() if i.activo]
            total_max = sum(i.escala_max for i in indicadores_activos)
            total_ind = len(indicadores_activos)
        actividades.append({
            "obj": a,
            "total_indicadores": total_ind,
            "total_maximo": total_max,
        })

    return render(request, "libro_docente/actividad_list.html", {
        "asignacion": asignacion,
        "actividades": actividades,
        "periodos_cl": periodos_cl,
        "periodo_id": str(periodo_id) if periodo_id else None,
        "tipo": tipo,
        "orden": orden,
        "available_tipos": available_tipos,
    })


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def actividad_create_view(request, asignacion_id):
    """
    Crear actividad de evaluación.
    Requiere periodo y tipo por GET.
    """
    asignacion = _obtener_asignacion_con_permiso(request, asignacion_id)
    if asignacion is None:
        messages.error(request, "No tienes acceso a esta asignación.")
        return redirect("libro_docente:home")

    inst_id = asignacion.subarea_curso.institucion_id
    if getattr(request, "institucion_activa_id", None) and inst_id != request.institucion_activa_id:
        messages.error(request, "No puedes crear actividades en otra institución.")
        return redirect("libro_docente:home")

    periodo_id = request.GET.get("periodo")
    tipo = request.GET.get("tipo", "").upper()
    tipos_habilitados = _tipos_habilitados_por_esquema(asignacion)
    if not periodo_id or tipo not in TIPOS_EVALUACION:
        messages.error(request, "Debe indicar periodo y tipo válido.")
        return redirect(reverse("libro_docente:actividad_list", args=[asignacion_id]))
    if tipo not in tipos_habilitados:
        messages.error(request, "Ese componente no está habilitado en el esquema de esta asignación.")
        return redirect(reverse("libro_docente:actividad_list", args=[asignacion_id]))

    pcl = get_object_or_404(
        PeriodoCursoLectivo.objects.filter(
            institucion_id=inst_id,
            curso_lectivo=asignacion.curso_lectivo,
            activo=True,
        ).select_related("periodo"),
        periodo_id=int(periodo_id),
    )
    periodo = pcl.periodo

    if request.method == "POST":
        post_data = request.POST.copy()
        post_data.setdefault("tipo_componente", tipo)
        post_data.setdefault("estado", ActividadEvaluacion.BORRADOR)
        post_data.setdefault("descripcion", "")
        post_data.setdefault("alcance_estudiantes", ActividadEvaluacion.ALCANCE_TODOS)
        form = ActividadEvaluacionForm(post_data)
        if form.is_valid():
            if tipo in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO):
                disponible, pct_esquema, pct_usado = porcentaje_disponible_para_tipo(
                    asignacion, periodo.id, tipo
                )
                pct_nuevo = form.cleaned_data.get("porcentaje_actividad") or Decimal("0")
                if pct_nuevo > disponible:
                    if disponible <= 0:
                        form.add_error("porcentaje_actividad", f"Ya se completó el {pct_esquema}% permitido para {tipo.title()} en este período.")
                    else:
                        form.add_error(
                            "porcentaje_actividad",
                            f"Máximo disponible: {disponible}% (esquema {pct_esquema}%, usado {pct_usado}%).",
                        )
                    return render(request, "libro_docente/actividad_form.html", {
                        "form": form,
                        "formset": None,
                        "asignacion": asignacion,
                        "periodo": periodo,
                        "periodo_id": periodo_id,
                        "tipo": tipo,
                        "tipo_display": dict(ActividadEvaluacion.TIPO_CHOICES).get(tipo, tipo.title()),
                        "actividad": None,
                        "es_simple": True,
                    })
            with transaction.atomic():
                obj = form.save(commit=False)
                obj.docente_asignacion = asignacion
                obj.institucion_id = inst_id
                obj.curso_lectivo = asignacion.curso_lectivo
                obj.periodo = periodo
                obj.tipo_componente = tipo
                obj.created_by = request.user
                obj.save()
            if tipo in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO):
                messages.success(request, "Actividad creada. Puede calificar ahora.")
                return redirect(reverse("libro_docente:actividad_calificar", args=[obj.id]))
            messages.success(request, "Actividad creada. Agregue indicadores a continuación.")
            return redirect(reverse("libro_docente:actividad_edit", args=[obj.id]))
    else:
        form = ActividadEvaluacionForm(initial={
            "tipo_componente": tipo,
            "estado": ActividadEvaluacion.BORRADOR,
            "alcance_estudiantes": ActividadEvaluacion.ALCANCE_TODOS,
        })

    tipo_display = dict(ActividadEvaluacion.TIPO_CHOICES).get(tipo, tipo.title())
    return render(request, "libro_docente/actividad_form.html", {
        "form": form,
        "formset": None,
        "asignacion": asignacion,
        "periodo": periodo,
        "periodo_id": periodo_id,
        "tipo": tipo,
        "tipo_display": tipo_display,
        "actividad": None,
        "es_simple": tipo in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO),
    })


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def actividad_edit_view(request, actividad_id):
    """
    Editar actividad e indicadores.
    """
    actividad = get_object_or_404(
        ActividadEvaluacion.objects.select_related(
            "docente_asignacion__subarea_curso",
            "periodo",
            "institucion",
        ),
        pk=actividad_id,
    )

    if not puede_usuario_editar_actividad(actividad, request):
        messages.error(request, "No tienes permiso para editar esta actividad.")
        return redirect("libro_docente:home")

    inst_activa = getattr(request, "institucion_activa_id", None)
    if inst_activa and not actividad_pertenece_a_institucion(actividad, inst_activa):
        messages.error(request, "No puedes editar actividades de otra institución.")
        return redirect("libro_docente:home")

    es_simple = actividad.tipo_componente in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO)
    formset = None
    if request.method == "POST":
        post_data = request.POST.copy()
        post_data.setdefault("tipo_componente", actividad.tipo_componente)
        if es_simple:
            post_data.setdefault("estado", actividad.estado or ActividadEvaluacion.BORRADOR)
            post_data.setdefault("descripcion", actividad.descripcion or "")
            post_data.setdefault("alcance_estudiantes", actividad.alcance_estudiantes or ActividadEvaluacion.ALCANCE_TODOS)
        form = ActividadEvaluacionForm(post_data, instance=actividad)
        if not es_simple:
            formset = IndicadorActividadFormSet(request.POST, instance=actividad)
        valid = form.is_valid() and (es_simple or (formset and formset.is_valid()))
        if valid:
            if es_simple:
                disponible, pct_esquema, pct_usado = porcentaje_disponible_para_tipo(
                    actividad.docente_asignacion,
                    actividad.periodo_id,
                    actividad.tipo_componente,
                    actividad_excluir_id=actividad.id,
                )
                pct_nuevo = form.cleaned_data.get("porcentaje_actividad") or Decimal("0")
                if pct_nuevo > disponible:
                    if disponible <= 0:
                        form.add_error("porcentaje_actividad", f"Ya se completó el {pct_esquema}% permitido en este período.")
                    else:
                        form.add_error(
                            "porcentaje_actividad",
                            f"Máximo disponible: {disponible}% (esquema {pct_esquema}%, usado {pct_usado}%).",
                        )
                else:
                    with transaction.atomic():
                        form.save()
                    messages.success(request, "Actividad actualizada.")
                    return redirect(reverse("libro_docente:actividad_edit", args=[actividad_id]))
            else:
                with transaction.atomic():
                    form.save()
                    formset.save()
                    crear_copia_adecuacion = (
                        request.POST.get("crear_copia_adecuacion") == "1"
                        and actividad.tipo_componente in (ActividadEvaluacion.TAREA, ActividadEvaluacion.COTIDIANO)
                        and actividad.alcance_estudiantes != ActividadEvaluacion.ALCANCE_ADECUACION
                    )
                    if crear_copia_adecuacion:
                        ids_adecuacion = _get_ids_adecuacion(actividad.docente_asignacion)
                        if ids_adecuacion:
                            copia = duplicar_actividad(
                                actividad,
                                titulo_nuevo=f"{actividad.titulo} (Adecuación)",
                            )
                            copia.alcance_estudiantes = ActividadEvaluacion.ALCANCE_ADECUACION
                            copia.created_by = request.user
                            copia.save(update_fields=["alcance_estudiantes", "created_by"])
                messages.success(request, "Actividad actualizada.")
                return redirect(reverse("libro_docente:actividad_edit", args=[actividad_id]))
    else:
        form = ActividadEvaluacionForm(instance=actividad)
        if not es_simple:
            formset = IndicadorActividadFormSet(instance=actividad)

    total_maximo = (actividad.puntaje_total or 0) if es_simple else calcular_total_maximo_actividad(actividad)

    return render(request, "libro_docente/actividad_form.html", {
        "form": form,
        "formset": formset,
        "asignacion": actividad.docente_asignacion,
        "periodo": actividad.periodo,
        "periodo_id": actividad.periodo_id,
        "tipo": actividad.tipo_componente,
        "tipo_display": actividad.get_tipo_componente_display(),
        "actividad": actividad,
        "total_maximo": total_maximo,
        "es_simple": es_simple,
    })


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def actividad_delete_view(request, actividad_id):
    """
    Eliminar actividad (con confirmación por POST).
    """
    actividad = get_object_or_404(
        ActividadEvaluacion.objects.select_related("docente_asignacion"),
        pk=actividad_id,
    )

    if not puede_usuario_editar_actividad(actividad, request):
        messages.error(request, "No tienes permiso para eliminar esta actividad.")
        return redirect("libro_docente:home")

    inst_activa = getattr(request, "institucion_activa_id", None)
    if inst_activa and not actividad_pertenece_a_institucion(actividad, inst_activa):
        messages.error(request, "No puedes eliminar actividades de otra institución.")
        return redirect("libro_docente:home")

    asignacion_id = actividad.docente_asignacion_id

    if request.method == "POST":
        actividad.delete()
        messages.success(request, "Actividad eliminada.")
        return redirect(reverse("libro_docente:actividad_list", args=[asignacion_id]))

    return render(request, "libro_docente/actividad_confirm_delete.html", {
        "actividad": actividad,
        "asignacion": actividad.docente_asignacion,
    })


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def actividad_duplicar_view(request, actividad_id):
    """
    Duplicar actividad con sus indicadores (sin puntajes).
    """
    actividad = get_object_or_404(
        ActividadEvaluacion.objects.select_related("docente_asignacion").prefetch_related("indicadores"),
        pk=actividad_id,
    )

    if not puede_usuario_editar_actividad(actividad, request):
        messages.error(request, "No tienes permiso para duplicar esta actividad.")
        return redirect("libro_docente:home")

    inst_activa = getattr(request, "institucion_activa_id", None)
    if inst_activa and not actividad_pertenece_a_institucion(actividad, inst_activa):
        messages.error(request, "No puedes duplicar actividades de otra institución.")
        return redirect("libro_docente:home")

    if actividad.tipo_componente in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO):
        disponible, pct_esquema, pct_usado = porcentaje_disponible_para_tipo(
            actividad.docente_asignacion,
            actividad.periodo_id,
            actividad.tipo_componente,
        )
        pct_actividad = actividad.porcentaje_actividad or Decimal("0")
        if pct_actividad > disponible:
            messages.error(
                request,
                f"No se puede duplicar: disponible {disponible}% (esquema {pct_esquema}%, usado {pct_usado}%).",
            )
            return redirect(reverse("libro_docente:actividad_list", args=[actividad.docente_asignacion_id]))

    nueva = duplicar_actividad(actividad)
    nueva.created_by = request.user
    nueva.save(update_fields=["created_by"])
    messages.success(request, f"Copia creada: «{nueva.titulo}».")
    return redirect(reverse("libro_docente:actividad_edit", args=[nueva.id]))


def _asignaciones_destino_para_copiar(actividad, request):
    """
    Otras asignaciones del mismo docente, misma materia (subarea), mismo curso_lectivo,
    misma institución, distintas del grupo actual. Solo las que tienen el periodo.
    """
    asignacion_actual = actividad.docente_asignacion
    profesor = _get_profesor(request)
    if not profesor:
        return []
    if request.user.is_superuser:
        qs = DocenteAsignacion.objects.filter(activo=True)
    else:
        qs = DocenteAsignacion.objects.filter(docente=profesor, activo=True)
    inst_id = asignacion_actual.subarea_curso.institucion_id
    inst_activa = getattr(request, "institucion_activa_id", None)
    if inst_activa and inst_id != inst_activa:
        return []
    subarea_id = asignacion_actual.subarea_curso.subarea_id
    curso_lectivo_id = asignacion_actual.curso_lectivo_id
    periodo = actividad.periodo
    pcl_existe = PeriodoCursoLectivo.objects.filter(
        institucion_id=inst_id,
        curso_lectivo_id=curso_lectivo_id,
        periodo=periodo,
        activo=True,
    ).exists()
    if not pcl_existe:
        return []
    return list(
        qs.filter(
            subarea_curso__institucion_id=inst_id,
            subarea_curso__subarea_id=subarea_id,
            curso_lectivo_id=curso_lectivo_id,
        )
        .exclude(id=asignacion_actual.id)
        .select_related("subarea_curso__subarea", "seccion", "subgrupo__seccion")
        .order_by("seccion__nivel__numero", "seccion__numero", "subgrupo__letra")
    )


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def actividad_copiar_a_grupos_view(request, actividad_id):
    """
    Copiar actividad a otros grupos/asignaciones (misma materia, mismo curso lectivo).
    """
    actividad = get_object_or_404(
        ActividadEvaluacion.objects.select_related(
            "docente_asignacion__subarea_curso",
            "periodo",
        ).prefetch_related("indicadores"),
        pk=actividad_id,
    )

    if not puede_usuario_editar_actividad(actividad, request):
        messages.error(request, "No tienes permiso para copiar esta actividad.")
        return redirect("libro_docente:home")

    inst_activa = getattr(request, "institucion_activa_id", None)
    if inst_activa and not actividad_pertenece_a_institucion(actividad, inst_activa):
        messages.error(request, "No puedes copiar actividades de otra institución.")
        return redirect("libro_docente:home")

    asignaciones_destino = _asignaciones_destino_para_copiar(actividad, request)

    if request.method == "POST":
        ids_str = request.POST.getlist("asignacion_id")
        asignacion_ids = [int(x) for x in ids_str if str(x).isdigit()]
        if asignacion_ids:
            creadas = copiar_actividad_a_asignaciones(actividad, asignacion_ids, created_by=request.user)
            if creadas:
                messages.success(
                    request,
                    f"Actividad copiada a {len(creadas)} grupo(s): «{actividad.titulo}».",
                )
            else:
                messages.warning(request, "No se pudo copiar a ningún grupo. Verifique los destinos.")
        else:
            messages.warning(request, "Seleccione al menos un grupo destino.")
        return redirect(reverse("libro_docente:actividad_list", args=[actividad.docente_asignacion_id]))

    return render(request, "libro_docente/actividad_copiar_a_grupos.html", {
        "actividad": actividad,
        "asignacion": actividad.docente_asignacion,
        "asignaciones_destino": asignaciones_destino,
        "es_simple": actividad.tipo_componente in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO),
    })


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def actividad_calificar_view(request, actividad_id):
    """
    Grilla de calificación por estudiante e indicador.
    GET: muestra grilla con puntajes existentes.
    POST: guardado masivo de puntajes.
    """
    from decimal import Decimal

    actividad = get_object_or_404(
        ActividadEvaluacion.objects.select_related(
            "docente_asignacion__subarea_curso",
            "periodo",
        ).prefetch_related("indicadores"),
        pk=actividad_id,
    )

    if not puede_usuario_editar_actividad(actividad, request):
        messages.error(request, "No tienes permiso para calificar esta actividad.")
        return redirect("libro_docente:home")

    inst_activa = getattr(request, "institucion_activa_id", None)
    if inst_activa and not actividad_pertenece_a_institucion(actividad, inst_activa):
        messages.error(request, "No puedes calificar actividades de otra institución.")
        return redirect("libro_docente:home")

    asignacion = actividad.docente_asignacion
    matriculas = _get_estudiantes_para_actividad(asignacion, actividad)
    es_simple = actividad.tipo_componente in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO)
    if es_simple:
        return _calificar_simple(request, actividad, asignacion, matriculas)
    indicadores = list(actividad.indicadores.filter(activo=True).order_by("orden", "id"))
    total_maximo = calcular_total_maximo_actividad(actividad)

    # Cargar puntajes existentes
    puntajes_existentes = {}
    observaciones_existentes = {}
    if indicadores and matriculas:
        ind_ids = [ind.id for ind in indicadores]
        est_ids = [m.estudiante_id for m in matriculas]
        for p in PuntajeIndicador.objects.filter(
            indicador_id__in=ind_ids,
            estudiante_id__in=est_ids,
        ).select_related("indicador"):
            if p.puntaje_obtenido is not None:
                puntajes_existentes[(p.indicador_id, p.estudiante_id)] = p.puntaje_obtenido
        for o in ObservacionActividadEstudiante.objects.filter(
            actividad=actividad,
            estudiante_id__in=est_ids,
        ):
            observaciones_existentes[o.estudiante_id] = o.observacion or ""

    # POST: guardar puntajes
    if request.method == "POST":
        datos = {}
        observaciones_post = {}
        for ind in indicadores:
            for m in matriculas:
                key = f"p_{ind.id}_{m.estudiante_id}"
                val = request.POST.get(key)
                if val is not None:
                    datos[(ind.id, m.estudiante_id)] = val
        for m in matriculas:
            obs_key = f"obs_{m.estudiante_id}"
            observaciones_post[m.estudiante_id] = (request.POST.get(obs_key, "") or "").strip()
        with transaction.atomic():
            guardados, errores = guardar_puntajes_masivo(
                actividad,
                [m.estudiante_id for m in matriculas],
                datos,
                indicadores_ids={ind.id for ind in indicadores},
            )
            for est_id, obs_text in observaciones_post.items():
                if obs_text:
                    ObservacionActividadEstudiante.objects.update_or_create(
                        actividad=actividad,
                        estudiante_id=est_id,
                        defaults={"observacion": obs_text},
                    )
                else:
                    ObservacionActividadEstudiante.objects.filter(
                        actividad=actividad,
                        estudiante_id=est_id,
                    ).delete()
        if errores:
            for e in errores:
                messages.error(request, e)
        elif guardados > 0:
            messages.success(request, f"Se guardaron {guardados} puntaje(s).")
        else:
            messages.info(request, "No hubo cambios que guardar.")
        return redirect(reverse("libro_docente:actividad_calificar", args=[actividad_id]))

    # Construir filas para la grilla: cada fila tiene indicador_puntajes = [(ind, valor), ...]
    filas = []
    for m in matriculas:
        est = m.estudiante
        indicador_puntajes = [
            (ind, puntajes_existentes.get((ind.id, est.id)))
            for ind in indicadores
        ]
        total_obt = sum(
            (p or Decimal("0")) for _, p in indicador_puntajes
        )
        pct = (
            (total_obt / total_maximo * Decimal("100"))
            if total_maximo and total_maximo > 0
            else Decimal("0")
        )
        filas.append({
            "matricula": m,
            "estudiante": est,
            "indicador_puntajes": indicador_puntajes,
            "total_obtenido": total_obt,
            "porcentaje_logro": pct,
            "observacion_tarea": observaciones_existentes.get(est.id, ""),
        })

    # Orden por apellido (primer_apellido, segundo_apellido, nombres)
    filas.sort(
        key=lambda f: (
            (f["estudiante"].primer_apellido or "").upper(),
            (f["estudiante"].segundo_apellido or "").upper(),
            (f["estudiante"].nombres or "").upper(),
        )
    )

    return render(request, "libro_docente/calificacion.html", {
        "actividad": actividad,
        "asignacion": asignacion,
        "indicadores": indicadores,
        "filas": filas,
        "total_maximo": total_maximo,
        "total_estudiantes": len(filas),
    })


def _calificar_simple(request, actividad, asignacion, matriculas):
    puntaje_total = actividad.puntaje_total or Decimal("0")
    porcentaje_actividad = actividad.porcentaje_actividad or Decimal("0")
    if puntaje_total <= 0:
        messages.error(request, "Defina un valor en puntos válido antes de calificar.")
        return redirect(reverse("libro_docente:actividad_edit", args=[actividad.id]))

    est_ids = [m.estudiante_id for m in matriculas]
    puntajes_existentes = {
        p.estudiante_id: p.puntos_obtenidos
        for p in PuntajeSimple.objects.filter(actividad=actividad, estudiante_id__in=est_ids)
    }

    if request.method == "POST":
        errores = []
        cambios = []
        with transaction.atomic():
            for m in matriculas:
                key = f"ps_{m.estudiante_id}"
                raw = (request.POST.get(key, "") or "").strip()
                if raw == "":
                    cambios.append(("delete", m.estudiante_id, None))
                    continue
                try:
                    puntos = Decimal(raw.replace(",", "."))
                except Exception:
                    errores.append(f"{m.estudiante}: valor inválido.")
                    continue
                if puntos < 0 or puntos > puntaje_total or puntos != puntos.to_integral_value():
                    errores.append(
                        f"{m.estudiante}: puntaje fuera de rango (0 a {int(puntaje_total)})."
                    )
                    continue
                cambios.append(("upsert", m.estudiante_id, puntos))
            if errores:
                transaction.set_rollback(True)
            else:
                for op, est_id, pts in cambios:
                    if op == "delete":
                        PuntajeSimple.objects.filter(actividad=actividad, estudiante_id=est_id).delete()
                    else:
                        PuntajeSimple.objects.update_or_create(
                            actividad=actividad,
                            estudiante_id=est_id,
                            defaults={"puntos_obtenidos": pts},
                        )
        if errores:
            for e in errores[:5]:
                messages.error(request, e)
            if len(errores) > 5:
                messages.error(request, f"Se detectaron {len(errores)} errores de validación.")
            return redirect(reverse("libro_docente:actividad_calificar", args=[actividad.id]))
        messages.success(request, "Puntajes guardados.")
        return redirect(reverse("libro_docente:actividad_calificar", args=[actividad.id]))

    filas = []
    for m in matriculas:
        est = m.estudiante
        puntos = puntajes_existentes.get(est.id)
        nota = (puntos / puntaje_total * Decimal("100")) if (puntos is not None and puntaje_total > 0) else None
        porcentaje = (puntos / puntaje_total * porcentaje_actividad) if (puntos is not None and puntaje_total > 0) else None
        filas.append({
            "matricula": m,
            "estudiante": est,
            "puntos": puntos,
            "nota": nota,
            "porcentaje": porcentaje,
        })

    filas.sort(
        key=lambda f: (
            (f["estudiante"].primer_apellido or "").upper(),
            (f["estudiante"].segundo_apellido or "").upper(),
            (f["estudiante"].nombres or "").upper(),
        )
    )
    return render(request, "libro_docente/calificacion_simple.html", {
        "actividad": actividad,
        "asignacion": asignacion,
        "filas": filas,
        "puntaje_total": puntaje_total,
        "porcentaje_actividad": porcentaje_actividad,
        "total_estudiantes": len(filas),
    })


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def resumen_evaluacion_view(request, asignacion_id):
    """
    Resumen acumulado por componente (TAREAS / COTIDIANOS) por estudiante.
    Muestra obtenidos, máximos, % logro, % componente y aporte a nota final.
    """
    asignacion = _obtener_asignacion_con_permiso(request, asignacion_id)
    if asignacion is None:
        messages.error(request, "No tienes acceso.")
        return redirect("libro_docente:home")

    inst_id = asignacion.subarea_curso.institucion_id
    inst_activa = getattr(request, "institucion_activa_id", None)
    if inst_activa and inst_id != inst_activa:
        messages.error(request, "No puedes acceder a otra institución.")
        return redirect("libro_docente:home")

    periodos_cl = list(
        PeriodoCursoLectivo.objects
        .filter(institucion_id=inst_id, curso_lectivo=asignacion.curso_lectivo, activo=True)
        .select_related("periodo")
        .order_by("periodo__numero")
    )

    periodo_id_raw = request.GET.get("periodo")
    periodo_id = int(periodo_id_raw) if periodo_id_raw and str(periodo_id_raw).isdigit() else None
    tipo = request.GET.get("tipo", "").upper()
    if tipo not in TIPOS_EVALUACION:
        tipo = None
    if not periodo_id and periodos_cl:
        periodo_id = periodos_cl[0].periodo_id

    matriculas = _get_estudiantes(asignacion)
    filas = []
    filas_general = []
    has_proyecto = ActividadEvaluacion.PROYECTO in _tipos_habilitados_por_esquema(asignacion)
    if periodo_id:
        filas = calcular_resumen_evaluacion_completo(asignacion, periodo_id, matriculas)
        filas_general = _construir_resumen_general(asignacion, periodo_id, matriculas, filas)
        periodo_sel = (
            PeriodoCursoLectivo.objects
            .filter(
                institucion_id=asignacion.subarea_curso.institucion_id,
                curso_lectivo=asignacion.curso_lectivo,
                periodo_id=periodo_id,
                activo=True,
            )
            .select_related("periodo")
            .first()
        )
        asistencia_map = {}
        if periodo_sel:
            resumen_asis = _calcular_resumen(asignacion, periodo_sel.periodo, matriculas)
            asistencia_map = {r["estudiante"].id: r["aporte_real"] for r in resumen_asis.get("estudiantes", [])}
        for f in filas:
            aporte_asistencia = asistencia_map.get(f["estudiante"].id, Decimal("0"))
            f["asistencia"] = {"aporte": aporte_asistencia}
            f["nota_final"] = (
                (f.get("tareas", {}) or {}).get("aporte", Decimal("0"))
                + (f.get("cotidianos", {}) or {}).get("aporte", Decimal("0"))
                + (f.get("pruebas", {}) or {}).get("aporte", Decimal("0"))
                + (f.get("proyectos", {}) or {}).get("aporte", Decimal("0"))
                + aporte_asistencia
            )

    return render(request, "libro_docente/resumen_evaluacion.html", {
        "asignacion": asignacion,
        "periodos_cl": periodos_cl,
        "periodo_id": str(periodo_id) if periodo_id else None,
        "tipo": tipo,
        "filas": filas,
        "filas_general": filas_general,
        "has_proyecto": has_proyecto,
    })


def _construir_resumen_general(asignacion, periodo_id, matriculas, filas_eval):
    """
    Resumen final por estudiante para exportación.
    """
    periodo_sel = (
        PeriodoCursoLectivo.objects
        .filter(
            institucion_id=asignacion.subarea_curso.institucion_id,
            curso_lectivo=asignacion.curso_lectivo,
            periodo_id=periodo_id,
            activo=True,
        )
        .select_related("periodo")
        .first()
    )
    asist_por_est = {}
    if periodo_sel:
        resumen_asis = _calcular_resumen(asignacion, periodo_sel.periodo, matriculas)
        asist_por_est = {r["estudiante"].id: r["aporte_real"] for r in resumen_asis.get("estudiantes", [])}

    filas_por_est = {f["estudiante"].id: f for f in filas_eval}
    rows = []
    for m in matriculas:
        est = m.estudiante
        fe = filas_por_est.get(est.id, {})
        rows.append({
            "id": est.identificacion,
            "nombre": f"{est.primer_apellido} {est.segundo_apellido or ''} {est.nombres}".strip(),
            "cotidiano": (fe.get("cotidianos", {}) or {}).get("aporte", Decimal("0")),
            "tareas": (fe.get("tareas", {}) or {}).get("aporte", Decimal("0")),
            "pruebas": (fe.get("pruebas", {}) or {}).get("aporte", Decimal("0")),
            "proyecto": (fe.get("proyectos", {}) or {}).get("aporte", Decimal("0")),
            "asistencia": asist_por_est.get(est.id, Decimal("0")),
        })
    return rows


def _to_2_dec(valor):
    if valor is None:
        return Decimal("0.00")
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))
    return valor.quantize(Decimal("0.01"))


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def resumen_general_export_xlsx(request, asignacion_id):
    asignacion = _obtener_asignacion_con_permiso(request, asignacion_id)
    if asignacion is None:
        messages.error(request, "No tienes acceso.")
        return redirect("libro_docente:home")
    if openpyxl is None:
        messages.error(request, "openpyxl no está disponible en el servidor.")
        return redirect(reverse("libro_docente:resumen_evaluacion", args=[asignacion_id]))

    periodo_id_raw = request.GET.get("periodo")
    periodo_id = int(periodo_id_raw) if periodo_id_raw and str(periodo_id_raw).isdigit() else None
    if not periodo_id:
        messages.error(request, "Debe seleccionar período para exportar.")
        return redirect(reverse("libro_docente:resumen_evaluacion", args=[asignacion_id]))

    matriculas = _get_estudiantes(asignacion)
    filas = calcular_resumen_evaluacion_completo(asignacion, periodo_id, matriculas)
    filas_general = _construir_resumen_general(asignacion, periodo_id, matriculas, filas)
    has_proyecto = ActividadEvaluacion.PROYECTO in _tipos_habilitados_por_esquema(asignacion)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resumen General"
    headers = ["id", "Nombre", "Trabajo cotidiano", "Tareas", "Pruebas"]
    if has_proyecto:
        headers.append("Proyecto")
    headers.append("Asistencia")
    ws.append(headers)
    for r in filas_general:
        row = [
            r["id"],
            r["nombre"],
            float(_to_2_dec(r["cotidiano"])),
            float(_to_2_dec(r["tareas"])),
            float(_to_2_dec(r["pruebas"])),
        ]
        if has_proyecto:
            row.append(float(_to_2_dec(r["proyecto"])))
        row.append(float(_to_2_dec(r["asistencia"])))
        ws.append(row)

    resp = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="resumen_general_{asignacion_id}_{periodo_id}.xlsx"'
    wb.save(resp)
    return resp


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def resumen_general_export_csv(request, asignacion_id):
    asignacion = _obtener_asignacion_con_permiso(request, asignacion_id)
    if asignacion is None:
        messages.error(request, "No tienes acceso.")
        return redirect("libro_docente:home")

    periodo_id_raw = request.GET.get("periodo")
    periodo_id = int(periodo_id_raw) if periodo_id_raw and str(periodo_id_raw).isdigit() else None
    if not periodo_id:
        messages.error(request, "Debe seleccionar período para exportar.")
        return redirect(reverse("libro_docente:resumen_evaluacion", args=[asignacion_id]))

    matriculas = _get_estudiantes(asignacion)
    filas = calcular_resumen_evaluacion_completo(asignacion, periodo_id, matriculas)
    filas_general = _construir_resumen_general(asignacion, periodo_id, matriculas, filas)
    has_proyecto = ActividadEvaluacion.PROYECTO in _tipos_habilitados_por_esquema(asignacion)

    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="resumen_general_{asignacion_id}_{periodo_id}.csv"'
    writer = csv.writer(resp)
    headers = ["id", "Nombre", "Trabajo cotidiano", "Tareas", "Pruebas"]
    if has_proyecto:
        headers.append("Proyecto")
    headers.append("Asistencia")
    writer.writerow(headers)
    for r in filas_general:
        row = [
            r["id"],
            r["nombre"],
            f"{_to_2_dec(r['cotidiano']):.2f}",
            f"{_to_2_dec(r['tareas']):.2f}",
            f"{_to_2_dec(r['pruebas']):.2f}",
        ]
        if has_proyecto:
            row.append(f"{_to_2_dec(r['proyecto']):.2f}")
        row.append(f"{_to_2_dec(r['asistencia']):.2f}")
        writer.writerow(row)
    return resp


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def resumen_estudiante_detalle_view(request, asignacion_id, estudiante_id):
    """
    Detalle del resumen por estudiante: desglose por actividad.
    """
    asignacion = _obtener_asignacion_con_permiso(request, asignacion_id)
    if asignacion is None:
        messages.error(request, "No tienes acceso.")
        return redirect("libro_docente:home")

    matriculas = _get_estudiantes(asignacion)
    matricula = next((m for m in matriculas if m.estudiante_id == estudiante_id), None)
    if not matricula:
        messages.error(request, "El estudiante no pertenece a este grupo.")
        return redirect(reverse("libro_docente:resumen_evaluacion", args=[asignacion_id]))

    periodo_id_raw = request.GET.get("periodo")
    periodo_id = int(periodo_id_raw) if periodo_id_raw and str(periodo_id_raw).isdigit() else None
    tipo = request.GET.get("tipo", "").upper()
    if tipo not in TIPOS_EVALUACION:
        tipo = None
    inst_id = asignacion.subarea_curso.institucion_id
    periodos_cl = list(
        PeriodoCursoLectivo.objects
        .filter(institucion_id=inst_id, curso_lectivo=asignacion.curso_lectivo, activo=True)
        .select_related("periodo")
        .order_by("periodo__numero")
    )
    if not periodo_id and periodos_cl:
        periodo_id = periodos_cl[0].periodo_id

    from decimal import Decimal
    from .services import calcular_resumen_componente_estudiante

    _empty_resumen = {
        "puntos_obtenidos": Decimal("0"),
        "puntos_maximos": Decimal("0"),
        "porcentaje_logro": Decimal("0"),
        "porcentaje_componente": Decimal("0"),
        "aporte": Decimal("0"),
        "detalle_actividades": [],
    }
    tareas = (
        calcular_resumen_componente_estudiante(
            asignacion, periodo_id, ActividadEvaluacion.TAREA, estudiante_id
        )
        if periodo_id
        else _empty_resumen
    )
    cotidianos = (
        calcular_resumen_componente_estudiante(
            asignacion, periodo_id, ActividadEvaluacion.COTIDIANO, estudiante_id
        )
        if periodo_id
        else _empty_resumen
    )
    pruebas = (
        calcular_resumen_componente_estudiante(
            asignacion, periodo_id, ActividadEvaluacion.PRUEBA, estudiante_id
        )
        if periodo_id
        else _empty_resumen
    )
    proyectos = (
        calcular_resumen_componente_estudiante(
            asignacion, periodo_id, ActividadEvaluacion.PROYECTO, estudiante_id
        )
        if periodo_id
        else _empty_resumen
    )

    return render(request, "libro_docente/resumen_estudiante_detalle.html", {
        "asignacion": asignacion,
        "estudiante": matricula.estudiante,
        "periodos_cl": periodos_cl,
        "periodo_id": str(periodo_id) if periodo_id else None,
        "tipo": tipo,
        "tareas": tareas,
        "cotidianos": cotidianos,
        "pruebas": pruebas,
        "proyectos": proyectos,
    })
