from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from evaluaciones.models import (
    DocenteAsignacion,
    EsquemaEvalComponente,
    Periodo,
    PeriodoCursoLectivo,
)
from config_institucional.models import Profesor
from matricula.models import MatriculaAcademica

from .models import AsistenciaRegistro, AsistenciaSesion

# ─── Tabla MEP: % ausencias injustificadas → nota 0-10 ─────────────────────
# Cada tupla: (limite_inf_pct, limite_sup_pct, nota)
_MEP_TABLE = [
    (0,  0,   10),
    (1,  5,   9),
    (6,  10,  8),
    (11, 15,  7),
    (16, 20,  6),
    (21, 25,  5),
    (26, 30,  4),
    (31, 35,  3),
    (36, 40,  2),
    (41, 45,  1),
    (46, 100, 0),
]


def _nota_mep(pct: float) -> int:
    pct = round(pct, 4)
    for lo, hi, nota in _MEP_TABLE:
        if lo <= pct <= hi:
            return nota
    return 0


def _get_profesor(request):
    """Devuelve el primer Profesor del usuario según la institución activa."""
    qs = Profesor.objects.filter(usuario=request.user)
    inst_id = getattr(request, "institucion_activa_id", None)
    if inst_id:
        qs = qs.filter(institucion_id=inst_id)
    return qs.first()


def _get_estudiantes(asignacion):
    """
    Devuelve MatriculaAcademica activas del grupo de la asignación,
    ordenadas por apellido.
    """
    filtros = {"curso_lectivo": asignacion.curso_lectivo, "estado": "activo"}
    if asignacion.seccion_id:
        filtros["seccion_id"] = asignacion.seccion_id
    else:
        filtros["subgrupo_id"] = asignacion.subgrupo_id
    return (
        MatriculaAcademica.objects
        .filter(**filtros)
        .select_related("estudiante")
        .order_by("estudiante__primer_apellido", "estudiante__segundo_apellido", "estudiante__nombres")
    )


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
    Retorna dict con 'total_sesiones', 'peso_asistencia', 'estudiantes'.
    """
    sesiones = AsistenciaSesion.objects.filter(
        docente_asignacion=asignacion,
        periodo=periodo,
    ).order_by("fecha", "sesion_numero")

    total_sesiones = sesiones.count()
    sesion_ids = list(sesiones.values_list("id", flat=True))

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
    for m in matriculas:
        est = m.estudiante
        # Fecha de ingreso al grupo: usar fecha_asignacion de la matrícula
        # (preparado para usar fecha_ingreso si se agrega en el futuro)
        fecha_ingreso_grupo = m.fecha_asignacion

        # Contar sesiones desde que ingresó el estudiante
        sesiones_desde_ingreso = (
            AsistenciaSesion.objects
            .filter(id__in=sesion_ids, fecha__gte=fecha_ingreso_grupo)
            .count()
        ) if fecha_ingreso_grupo else total_sesiones

        agg = AsistenciaRegistro.objects.filter(
            sesion_id__in=sesion_ids,
            estudiante=est,
        ).aggregate(
            presentes=Count("id", filter=Q(estado=AsistenciaRegistro.PRESENTE)),
            tardias=Count("id", filter=Q(estado=AsistenciaRegistro.TARDIA)),
            ausentes_inj=Count("id", filter=Q(estado=AsistenciaRegistro.AUSENTE_INJUSTIFICADA)),
            ausentes_just=Count("id", filter=Q(estado=AsistenciaRegistro.AUSENTE_JUSTIFICADA)),
        )
        p   = agg["presentes"]  or 0
        t   = agg["tardias"]    or 0
        ai  = agg["ausentes_inj"] or 0
        aj  = agg["ausentes_just"] or 0

        # Sesiones sin registro cuentan como AI
        registradas = p + t + ai + aj
        ai_total = ai + max(0, sesiones_desde_ingreso - registradas)

        # Regla: cada 3 tardías = 1 ausencia equivalente
        tardia_equiv = t // 3
        total_equiv = ai_total + tardia_equiv

        pct = (total_equiv / sesiones_desde_ingreso * 100) if sesiones_desde_ingreso > 0 else 0
        nota_mep = _nota_mep(pct)

        aporte_real = Decimal(str(nota_mep)) * peso_asistencia / Decimal("100") if peso_asistencia else Decimal("0")

        # Indicador visual
        if pct == 0:
            nivel_alerta = "ok"
        elif pct <= 15:
            nivel_alerta = "warning"
        else:
            nivel_alerta = "danger"

        resultados.append({
            "estudiante": est,
            "presentes": p,
            "tardias": t,
            "ausentes_inj": ai_total,
            "ausentes_just": aj,
            "tardia_equiv": tardia_equiv,
            "total_equiv": total_equiv,
            "sesiones_consideradas": sesiones_desde_ingreso,
            "pct": round(pct, 1),
            "nota_mep": nota_mep,
            "peso_asistencia": peso_asistencia,
            "aporte_real": round(aporte_real, 2),
            "nivel_alerta": nivel_alerta,
        })

    nombre_componente = (
        comp_asistencia.componente.nombre if comp_asistencia else "Asistencia"
    )
    return {
        "total_sesiones": total_sesiones,
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
        raw = (
            DocenteAsignacion.objects
            .filter(docente=profesor, activo=True)
            .select_related(
                "subarea_curso__subarea",
                "curso_lectivo",
                "seccion__nivel",
                "subgrupo__seccion__nivel",
                "eval_scheme_snapshot",
            )
            .order_by("curso_lectivo__anio", "subarea_curso__subarea__nombre")
        )

        hoy = timezone.localdate()
        for a in raw:
            # Componentes del esquema snapshot
            componentes = []
            if a.eval_scheme_snapshot_id:
                componentes = list(
                    EsquemaEvalComponente.objects
                    .filter(esquema=a.eval_scheme_snapshot)
                    .select_related("componente")
                    .order_by("componente__nombre")
                )

            tiene_asistencia = any(
                c.componente.codigo.upper() in ("ASISTENCIA", "ASIS") or
                "ASISTENCIA" in c.componente.nombre.upper()
                for c in componentes
            )

            # Sesiones ya registradas hoy
            sesiones_hoy = AsistenciaSesion.objects.filter(
                docente_asignacion=a, fecha=hoy
            ).count()

            # Etiqueta del grupo
            if a.seccion_id:
                grupo_label = f"Sección {a.seccion}"
            elif a.subgrupo_id:
                grupo_label = f"Subgrupo {a.subgrupo}"
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
def asistencia_view(request, asignacion_id):
    """
    Pantalla de asistencia: selector de fecha + sesión, lista de estudiantes
    con toggles P/T/AI/AJ. Maneja GET (mostrar) y POST (guardar).
    """
    profesor = _get_profesor(request)
    if not profesor:
        messages.error(request, "No tienes perfil de docente en esta institución.")
        return redirect("libro_docente:home")

    asignacion = get_object_or_404(
        DocenteAsignacion, id=asignacion_id, docente=profesor, activo=True
    )

    # ── Fecha ────────────────────────────────────────────────────────────
    hoy = timezone.localdate()
    fecha_str = (request.POST if request.method == "POST" else request.GET).get("fecha")
    try:
        fecha = date.fromisoformat(fecha_str) if fecha_str else hoy
    except ValueError:
        fecha = hoy

    # ── Sesión ───────────────────────────────────────────────────────────
    try:
        sesion_num = int(
            (request.POST if request.method == "POST" else request.GET).get("sesion", 0)
        )
    except (ValueError, TypeError):
        sesion_num = 0

    # ── POST: guardar sesión ─────────────────────────────────────────────
    if request.method == "POST":
        if sesion_num <= 0:
            sesion_num = 1
        periodo = _infer_periodo(asignacion, fecha)
        inst_id = asignacion.subarea_curso.institucion_id

        try:
            with transaction.atomic():
                sesion, _ = AsistenciaSesion.objects.get_or_create(
                    docente_asignacion=asignacion,
                    periodo=periodo,
                    fecha=fecha,
                    sesion_numero=sesion_num,
                    defaults={
                        "institucion_id": inst_id,
                        "curso_lectivo": asignacion.curso_lectivo,
                        "created_by": request.user,
                    },
                )
                matriculas = _get_estudiantes(asignacion)
                bulk_create = []
                bulk_update = []
                existing = {r.estudiante_id: r for r in sesion.registros.all()}

                for m in matriculas:
                    est_id = m.estudiante_id
                    raw_estado = request.POST.get(f"estado_{est_id}", AsistenciaRegistro.PRESENTE)
                    estado = raw_estado if raw_estado in dict(AsistenciaRegistro.ESTADO_CHOICES) else AsistenciaRegistro.PRESENTE
                    obs = request.POST.get(f"obs_{est_id}", "")[:255]

                    if est_id in existing:
                        reg = existing[est_id]
                        reg.estado = estado
                        reg.observacion = obs
                        bulk_update.append(reg)
                    else:
                        bulk_create.append(
                            AsistenciaRegistro(sesion=sesion, estudiante_id=est_id, estado=estado, observacion=obs)
                        )

                if bulk_create:
                    AsistenciaRegistro.objects.bulk_create(bulk_create)
                if bulk_update:
                    AsistenciaRegistro.objects.bulk_update(bulk_update, ["estado", "observacion"])

            messages.success(request, f"✔ Sesión {sesion_num} del {fecha.strftime('%d/%m/%Y')} guardada.")
        except Exception as exc:
            messages.error(request, f"Error al guardar: {exc}")

        return redirect(f"{request.path}?fecha={fecha}&sesion={sesion_num}")

    # ── GET ──────────────────────────────────────────────────────────────
    sesiones_existentes = list(
        AsistenciaSesion.objects
        .filter(docente_asignacion=asignacion, fecha=fecha)
        .order_by("sesion_numero")
    )
    numeros = [s.sesion_numero for s in sesiones_existentes]
    siguiente_num = (max(numeros) + 1) if numeros else 1

    if sesion_num <= 0:
        sesion_num = numeros[0] if numeros else 1

    sesion_actual = next((s for s in sesiones_existentes if s.sesion_numero == sesion_num), None)

    # Estados guardados de la sesión seleccionada
    estados_guardados = {}
    obs_guardadas = {}
    if sesion_actual:
        for reg in sesion_actual.registros.select_related("estudiante"):
            estados_guardados[reg.estudiante_id] = reg.estado
            obs_guardadas[reg.estudiante_id] = reg.observacion

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
            "observacion": obs_guardadas.get(est.id, ""),
        })

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
        "sesion_num": sesion_num,
        "numeros": numeros,
        "siguiente_num": siguiente_num,
        "sesion_actual": sesion_actual,
        "estudiantes": estudiantes,
        "total_estudiantes": len(estudiantes),
        "periodo": periodo,
        "periodos_cl": periodos_cl,
        "PRESENTE": AsistenciaRegistro.PRESENTE,
        "TARDIA": AsistenciaRegistro.TARDIA,
        "AI": AsistenciaRegistro.AUSENTE_INJUSTIFICADA,
        "AJ": AsistenciaRegistro.AUSENTE_JUSTIFICADA,
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
        DocenteAsignacion, id=asignacion_id, docente=profesor, activo=True
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

    resumen = {"total_sesiones": 0, "peso_asistencia": Decimal("0"), "tiene_componente": False, "estudiantes": []}
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
