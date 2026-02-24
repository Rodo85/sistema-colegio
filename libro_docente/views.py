from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Count, Prefetch, Q
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
from .services import (
    actividad_pertenece_a_institucion,
    calcular_resumen_evaluacion_completo,
    calcular_total_maximo_actividad,
    duplicar_actividad,
    guardar_puntajes_masivo,
    puede_usuario_editar_actividad,
)

# ─── Tabla: % ausencias injustificadas → puntaje base (0-10) ─────────────────
# Rangos: [min_inclusive, max_exclusive) → puntaje
# 0% a <1% => 10, 1% a <10% => 9, 10% a <20% => 8, ..., 90% a 100% => 0
_MEP_RANGES = [
    (0, 1, 10),
    (1, 10, 9),
    (10, 20, 8),
    (20, 30, 7),
    (30, 40, 6),
    (40, 50, 5),
    (50, 60, 4),
    (60, 70, 3),
    (70, 80, 2),
    (80, 90, 1),
    (90, 100.01, 0),  # 90% a 100% inclusive
]


def _nota_mep(pct: float) -> int:
    """Convierte % ausencias injustificadas a puntaje base 0-10."""
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
    Optimizado: 1 query para sesiones, 1 para agregados por estudiante.
    """
    sesiones = AsistenciaSesion.objects.filter(
        docente_asignacion=asignacion,
        periodo=periodo,
    ).order_by("fecha", "sesion_numero")

    total_sesiones = sesiones.count()
    sesion_ids = list(sesiones.values_list("id", flat=True))
    fechas_sesion = dict(sesiones.values_list("id", "fecha"))

    # Agregados P/T/AI/AJ por estudiante en una sola query
    agregados = {
        row["estudiante_id"]: row
        for row in AsistenciaRegistro.objects.filter(sesion_id__in=sesion_ids)
        .values("estudiante_id")
        .annotate(
            presentes=Count("id", filter=Q(estado=AsistenciaRegistro.PRESENTE)),
            tardias=Count("id", filter=Q(estado=AsistenciaRegistro.TARDIA)),
            ausentes_inj=Count("id", filter=Q(estado=AsistenciaRegistro.AUSENTE_INJUSTIFICADA)),
            ausentes_just=Count("id", filter=Q(estado=AsistenciaRegistro.AUSENTE_JUSTIFICADA)),
        )
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
    for m in matriculas:
        est = m.estudiante
        # Fecha de ingreso al grupo: usar fecha_asignacion de la matrícula
        fecha_ingreso_grupo = m.fecha_asignacion

        # Contar sesiones desde que ingresó (en memoria, sin query)
        sesiones_desde_ingreso = (
            sum(1 for sid in sesion_ids if fechas_sesion.get(sid) >= fecha_ingreso_grupo)
            if fecha_ingreso_grupo else total_sesiones
        )

        agg = agregados.get(est.id, {})
        p   = agg.get("presentes", 0) or 0
        t   = agg.get("tardias", 0) or 0
        ai  = agg.get("ausentes_inj", 0) or 0
        aj  = agg.get("ausentes_just", 0) or 0

        # Sesiones sin registro cuentan como AI
        registradas = p + t + ai + aj
        ai_total = ai + max(0, sesiones_desde_ingreso - registradas)

        # Regla: cada 3 tardías = 1 ausencia equivalente
        tardia_equiv = t // 3
        total_equiv = ai_total + tardia_equiv

        pct = (total_equiv / sesiones_desde_ingreso * 100) if sesiones_desde_ingreso > 0 else 0
        puntaje_base = _nota_mep(pct)
        # aporte_real = (puntaje_base / 10) * peso_asistencia_esquema
        aporte_real = (
            Decimal(str(puntaje_base)) / Decimal("10") * peso_asistencia
            if peso_asistencia else Decimal("0")
        )

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
            componentes = list(a.eval_scheme_snapshot.componentes_esquema.all()) if a.eval_scheme_snapshot_id else []

            tiene_asistencia = any(
                c.componente.codigo.upper() in ("ASISTENCIA", "ASIS") or
                "ASISTENCIA" in (c.componente.nombre or "").upper()
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
            historial.append({
                "fecha": reg.sesion.fecha,
                "sesion_numero": reg.sesion.sesion_numero,
                "estado": reg.estado,
                "estado_display": reg.get_estado_display(),
                "observacion": reg.observacion or "",
            })
        # Sesiones sin registro (cuentan como AI)
        sesiones_data = {s.id: (s.fecha, s.sesion_numero) for s in sesiones}
        registradas_sesion_ids = {r.sesion_id for r in registros}
        for sid, (f, num) in sesiones_data.items():
            if sid not in registradas_sesion_ids:
                historial.append({
                    "fecha": f,
                    "sesion_numero": num,
                    "estado": AsistenciaRegistro.AUSENTE_INJUSTIFICADA,
                    "estado_display": "Ausente injustificada",
                    "observacion": "(sin registro)",
                })
        historial.sort(key=lambda x: (x["fecha"], x["sesion_numero"]))

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

    periodo_id_raw = request.GET.get("periodo")
    periodo_id = int(periodo_id_raw) if periodo_id_raw and str(periodo_id_raw).isdigit() else None
    tipo = request.GET.get("tipo", "").upper()

    qs = ActividadEvaluacion.objects.filter(
        docente_asignacion=asignacion,
        institucion_id=inst_id,
    ).select_related("periodo").prefetch_related("indicadores").order_by("-created_at")

    if periodo_id:
        qs = qs.filter(periodo_id=periodo_id)
    if tipo in ("TAREA", "COTIDIANO"):
        qs = qs.filter(tipo_componente=tipo)

    actividades_raw = list(qs)
    actividades = []
    for a in actividades_raw:
        indicadores_activos = [i for i in a.indicadores.all() if i.activo]
        total_max = sum(i.escala_max for i in indicadores_activos)
        actividades.append({
            "obj": a,
            "total_indicadores": len(indicadores_activos),
            "total_maximo": total_max,
        })

    return render(request, "libro_docente/actividad_list.html", {
        "asignacion": asignacion,
        "actividades": actividades,
        "periodos_cl": periodos_cl,
        "periodo_id": str(periodo_id) if periodo_id else None,
        "tipo": tipo,
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
    if not periodo_id or tipo not in ("TAREA", "COTIDIANO"):
        messages.error(request, "Debe indicar periodo y tipo (TAREA o COTIDIANO).")
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
        form = ActividadEvaluacionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                obj = form.save(commit=False)
                obj.docente_asignacion = asignacion
                obj.institucion_id = inst_id
                obj.curso_lectivo = asignacion.curso_lectivo
                obj.periodo = periodo
                obj.tipo_componente = tipo
                obj.created_by = request.user
                obj.save()
            messages.success(request, "Actividad creada. Agregue indicadores a continuación.")
            return redirect(reverse("libro_docente:actividad_edit", args=[obj.id]))
    else:
        form = ActividadEvaluacionForm(initial={
            "tipo_componente": tipo,
            "estado": ActividadEvaluacion.BORRADOR,
        })

    tipo_display = "Tarea" if tipo == "TAREA" else "Cotidiano"
    return render(request, "libro_docente/actividad_form.html", {
        "form": form,
        "formset": None,
        "asignacion": asignacion,
        "periodo": periodo,
        "periodo_id": periodo_id,
        "tipo": tipo,
        "tipo_display": tipo_display,
        "actividad": None,
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

    if request.method == "POST":
        form = ActividadEvaluacionForm(request.POST, instance=actividad)
        formset = IndicadorActividadFormSet(request.POST, instance=actividad)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, "Actividad actualizada.")
            return redirect(reverse("libro_docente:actividad_edit", args=[actividad_id]))
        else:
            formset = IndicadorActividadFormSet(request.POST, instance=actividad)
    else:
        form = ActividadEvaluacionForm(instance=actividad)
        formset = IndicadorActividadFormSet(instance=actividad)

    total_maximo = calcular_total_maximo_actividad(actividad)

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

    nueva = duplicar_actividad(actividad)
    nueva.created_by = request.user
    nueva.save(update_fields=["created_by"])
    messages.success(request, f"Actividad duplicada: «{nueva.titulo}».")
    return redirect(reverse("libro_docente:actividad_edit", args=[nueva.id]))


@login_required
@permission_required("libro_docente.access_libro_docente", raise_exception=True)
def actividad_calificar_view(request, actividad_id):
    """
    Grilla de calificación por estudiante e indicador.
    GET: muestra grilla con puntajes existentes.
    POST: guardado masivo de puntajes.
    """
    from decimal import Decimal, InvalidOperation

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
    indicadores = list(actividad.indicadores.filter(activo=True).order_by("orden", "id"))
    matriculas = _get_estudiantes(asignacion)
    total_maximo = calcular_total_maximo_actividad(actividad)

    # Cargar puntajes existentes
    puntajes_existentes = {}
    if indicadores and matriculas:
        ind_ids = [ind.id for ind in indicadores]
        est_ids = [m.estudiante_id for m in matriculas]
        for p in PuntajeIndicador.objects.filter(
            indicador_id__in=ind_ids,
            estudiante_id__in=est_ids,
        ).select_related("indicador"):
            if p.puntaje_obtenido is not None:
                puntajes_existentes[(p.indicador_id, p.estudiante_id)] = p.puntaje_obtenido

    # POST: guardar puntajes
    if request.method == "POST":
        datos = {}
        for ind in indicadores:
            for m in matriculas:
                key = f"p_{ind.id}_{m.estudiante_id}"
                val = request.POST.get(key)
                if val is not None:
                    datos[(ind.id, m.estudiante_id)] = val
        with transaction.atomic():
            guardados, errores = guardar_puntajes_masivo(
                actividad,
                [m.estudiante_id for m in matriculas],
                datos,
                indicadores_ids={ind.id for ind in indicadores},
            )
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
        })

    return render(request, "libro_docente/calificacion.html", {
        "actividad": actividad,
        "asignacion": asignacion,
        "indicadores": indicadores,
        "filas": filas,
        "total_maximo": total_maximo,
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
    if not periodo_id and periodos_cl:
        periodo_id = periodos_cl[0].periodo_id

    matriculas = _get_estudiantes(asignacion)
    filas = []
    if periodo_id:
        filas = calcular_resumen_evaluacion_completo(asignacion, periodo_id, matriculas)

    return render(request, "libro_docente/resumen_evaluacion.html", {
        "asignacion": asignacion,
        "periodos_cl": periodos_cl,
        "periodo_id": str(periodo_id) if periodo_id else None,
        "filas": filas,
    })


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

    return render(request, "libro_docente/resumen_estudiante_detalle.html", {
        "asignacion": asignacion,
        "estudiante": matricula.estudiante,
        "periodos_cl": periodos_cl,
        "periodo_id": str(periodo_id) if periodo_id else None,
        "tareas": tareas,
        "cotidianos": cotidianos,
    })
