"""
Servicios para el módulo de evaluación por indicadores (TAREAS/COTIDIANOS).
Cálculos, validaciones y helpers CRUD.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q, Sum

# Redondeo consistente: 2 decimales en cálculos y visualización
DECIMAL_PLACES = 2


def _redondear(valor):
    """Redondea un Decimal a DECIMAL_PLACES decimales."""
    if valor is None:
        return None
    q = Decimal("0.01") if DECIMAL_PLACES == 2 else Decimal(10) ** (-DECIMAL_PLACES)
    return valor.quantize(q, rounding=ROUND_HALF_UP)


from evaluaciones.models import EsquemaEvalComponente

from .models import ActividadEvaluacion, IndicadorActividad, PuntajeIndicador, PuntajeSimple


def calcular_total_maximo_actividad(actividad):
    """
    Suma de escala_max de indicadores activos de la actividad.
    """
    if not actividad or not actividad.pk:
        return Decimal("0")
    return (
        IndicadorActividad.objects.filter(actividad=actividad, activo=True)
        .aggregate(total=Sum("escala_max"))["total"]
        or Decimal("0")
    )


def calcular_total_obtenido_estudiante(actividad, estudiante_id):
    """
    Suma de puntaje_obtenido del estudiante en esa actividad.
    Solo considera indicadores activos. NULL se trata como 0.
    """
    if not actividad or not actividad.pk or not estudiante_id:
        return Decimal("0")
    indicadores_ids = list(
        IndicadorActividad.objects.filter(actividad=actividad, activo=True).values_list("id", flat=True)
    )
    if not indicadores_ids:
        return Decimal("0")
    total = (
        PuntajeIndicador.objects.filter(
            indicador_id__in=indicadores_ids,
            estudiante_id=estudiante_id,
        )
        .exclude(puntaje_obtenido__isnull=True)
        .aggregate(s=Sum("puntaje_obtenido"))["s"]
        or Decimal("0")
    )
    return total


def calcular_porcentaje_logro(actividad, estudiante_id):
    """
    (total_obtenido / total_maximo) * 100 si total_maximo > 0, si no 0.
    """
    total_max = calcular_total_maximo_actividad(actividad)
    if total_max <= 0:
        return Decimal("0")
    total_obt = calcular_total_obtenido_estudiante(actividad, estudiante_id)
    return (total_obt / total_max) * Decimal("100")


def obtener_resumen_actividad_estudiante(actividad, estudiante_id):
    """
    Devuelve dict con total_maximo, total_obtenido, porcentaje_logro.
    """
    total_max = calcular_total_maximo_actividad(actividad)
    total_obt = calcular_total_obtenido_estudiante(actividad, estudiante_id)
    pct = (total_obt / total_max * Decimal("100")) if total_max > 0 else Decimal("0")
    return {
        "total_maximo": total_max,
        "total_obtenido": total_obt,
        "porcentaje_logro": pct,
    }


def validar_puntaje_en_rango(indicador, valor):
    """
    Valida que valor esté entre escala_min y escala_max del indicador.
    Lanza ValidationError si no cumple.
    """
    from django.core.exceptions import ValidationError

    if valor is None:
        return
    ind = indicador
    if valor < 0:
        raise ValueError("El puntaje debe ser >= 0.")
    if valor != valor.to_integral_value():
        raise ValueError("El puntaje debe ser un número entero (sin decimales).")
    if ind.escala_min is not None and valor < ind.escala_min:
        raise ValueError(f"El puntaje {valor} debe ser >= {ind.escala_min}.")
    if ind.escala_max is not None and valor > ind.escala_max:
        raise ValueError(f"El puntaje {valor} debe ser <= {ind.escala_max}.")


def guardar_puntajes_masivo(actividad, estudiante_ids, datos_puntajes, indicadores_ids=None):
    """
    Guarda puntajes en masa.
    datos_puntajes: dict (indicador_id, estudiante_id) -> puntaje_obtenido (Decimal o None)
    Valida que indicador pertenezca a actividad y estudiante esté en estudiante_ids.
    Retorna (guardados, errores) donde errores es lista de mensajes.
    """
    from decimal import Decimal, InvalidOperation

    if indicadores_ids is None:
        indicadores_ids = set(
            IndicadorActividad.objects.filter(actividad=actividad, activo=True).values_list("id", flat=True)
        )
    estudiante_ids_set = set(estudiante_ids)
    indicadores = {
        ind.id: ind
        for ind in IndicadorActividad.objects.filter(
            id__in=indicadores_ids, actividad=actividad
        )
    }
    errores = []
    guardados = 0

    for (ind_id, est_id), valor in datos_puntajes.items():
        if ind_id not in indicadores_ids or est_id not in estudiante_ids_set:
            continue
        if ind_id not in indicadores:
            continue
        ind = indicadores[ind_id]
        puntaje = None
        if valor is not None and str(valor).strip() != "":
            try:
                puntaje = Decimal(str(valor).strip().replace(",", "."))
            except (InvalidOperation, ValueError):
                errores.append(f"Valor no numérico en estudiante {est_id}, indicador {ind_id}.")
                continue
            try:
                validar_puntaje_en_rango(ind, puntaje)
            except ValueError as e:
                errores.append(str(e))
                continue

        obj, created = PuntajeIndicador.objects.update_or_create(
            indicador_id=ind_id,
            estudiante_id=est_id,
            defaults={"puntaje_obtenido": puntaje},
        )
        guardados += 1

    return guardados, errores


def guardar_o_actualizar_puntaje(indicador_id, estudiante_id, puntaje_obtenido, observacion=""):
    """
    Crea o actualiza el PuntajeIndicador.
    Valida que el indicador pertenezca a una actividad y que puntaje esté en rango.
    """
    from django.core.exceptions import ValidationError

    indicador = IndicadorActividad.objects.filter(pk=indicador_id).select_related("actividad").first()
    if not indicador:
        raise ValueError("Indicador no encontrado.")
    if puntaje_obtenido is not None:
        validar_puntaje_en_rango(indicador, puntaje_obtenido)

    obj, created = PuntajeIndicador.objects.update_or_create(
        indicador_id=indicador_id,
        estudiante_id=estudiante_id,
        defaults={
            "puntaje_obtenido": puntaje_obtenido,
            "observacion": observacion or "",
        },
    )
    return obj


def puede_docente_editar_actividad(actividad, profesor):
    """
    Verifica si el docente (Profesor) puede editar la actividad.
    """
    if not actividad or not profesor:
        return False
    return actividad.docente_asignacion.docente_id == profesor.id


def puede_usuario_editar_actividad(actividad, request):
    """
    Superadmin: sí. Docente normal: solo si es su asignación.
    """
    if request.user.is_superuser:
        return True
    from .views import _get_profesor

    profesor = _get_profesor(request)
    return puede_docente_editar_actividad(actividad, profesor)


# ═══════════════════════════════════════════════════════════════════════════
#  RESUMEN ACUMULADO POR COMPONENTE (Fase 4)
# ═══════════════════════════════════════════════════════════════════════════

# Regla MVP: actividades que cuentan en el acumulado
# - Estados: ACTIVA o CERRADA (no BORRADOR)
# - Con al menos un indicador activo
# - Permite parciales: actividades sin puntajes aportan 0 a obtenidos pero sí a máximos
ACTIVIDADES_ACUMULADO_ESTADOS = (ActividadEvaluacion.ACTIVA, ActividadEvaluacion.CERRADA)

# Mapeo tipo ActividadEvaluacion -> códigos ComponenteEval para buscar % en esquema
TIPO_TO_CODIGO_ESQUEMA = {
    ActividadEvaluacion.TAREA: ["TAREAS", "TAREA", "TAR"],
    ActividadEvaluacion.COTIDIANO: ["COTIDIANO", "COT"],
    ActividadEvaluacion.PRUEBA: ["PRUEBA", "PRUEBAS", "PRU"],
    ActividadEvaluacion.PROYECTO: ["PROYECTO", "PROYECTOS", "PRO"],
}


def obtener_porcentaje_componente_esquema(asignacion, tipo_componente):
    """
    Obtiene el % del componente en el esquema de la asignación.
    tipo_componente: TAREA o COTIDIANO.
    Retorna Decimal o 0 si no existe.
    """
    from django.db.models import Q

    if not asignacion or not asignacion.eval_scheme_snapshot_id:
        return Decimal("0")
    codigos = TIPO_TO_CODIGO_ESQUEMA.get(tipo_componente, [tipo_componente])
    tipo_nombres = {
        ActividadEvaluacion.TAREA: "tarea",
        ActividadEvaluacion.COTIDIANO: "cotid",
        ActividadEvaluacion.PRUEBA: "prueb",
        ActividadEvaluacion.PROYECTO: "proyect",
    }
    tipo_nombre = tipo_nombres.get(tipo_componente, tipo_componente.lower())
    comp = (
        EsquemaEvalComponente.objects
        .filter(esquema=asignacion.eval_scheme_snapshot)
        .filter(
            Q(componente__codigo__in=codigos) |
            Q(componente__codigo__iexact=tipo_componente) |
            Q(componente__nombre__icontains=tipo_nombre)
        )
        .select_related("componente")
        .first()
    )
    return comp.porcentaje if comp else Decimal("0")


def calcular_resumen_componente_estudiante(asignacion, periodo_id, tipo_componente, estudiante_id):
    """
    Calcula para un estudiante y componente:
    - puntos_obtenidos, puntos_maximos, porcentaje_logro, porcentaje_componente, aporte
    - detalle_actividades: [(actividad, max_act, obt_act), ...]
    """
    from django.db.models import Sum

    es_simple = tipo_componente in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO)
    actividades = (
        ActividadEvaluacion.objects
        .filter(
            docente_asignacion=asignacion,
            periodo_id=periodo_id,
            tipo_componente=tipo_componente,
            estado__in=ACTIVIDADES_ACUMULADO_ESTADOS,
        )
        .prefetch_related("indicadores")
        .order_by("titulo")
    )

    puntos_obtenidos = Decimal("0")
    puntos_maximos = Decimal("0")
    detalle = []

    for act in actividades:
        if es_simple:
            max_act = act.puntaje_total or Decimal("0")
            if max_act <= 0:
                continue
            ps = (
                PuntajeSimple.objects
                .filter(actividad=act, estudiante_id=estudiante_id)
                .values_list("puntos_obtenidos", flat=True)
                .first()
            )
            obt_act = ps if ps is not None else Decimal("0")
            detalle_indicadores = []
        else:
            ind_ids = list(act.indicadores.filter(activo=True).values_list("id", flat=True))
            if not ind_ids:
                continue
            max_act = (
                IndicadorActividad.objects.filter(actividad=act, activo=True)
                .aggregate(s=Sum("escala_max"))["s"] or Decimal("0")
            )
            obt_act = (
                PuntajeIndicador.objects
                .filter(indicador_id__in=ind_ids, estudiante_id=estudiante_id)
                .exclude(puntaje_obtenido__isnull=True)
                .aggregate(s=Sum("puntaje_obtenido"))["s"] or Decimal("0")
            )
            indicadores_act = list(act.indicadores.filter(activo=True).order_by("orden", "id"))
            puntajes_raw = list(
                PuntajeIndicador.objects.filter(
                    indicador_id__in=ind_ids, estudiante_id=estudiante_id
                ).values("indicador_id", "puntaje_obtenido")
            )
            puntajes_ind = {p["indicador_id"]: p["puntaje_obtenido"] for p in puntajes_raw}
            detalle_indicadores = [
                {"indicador": ind, "puntaje": puntajes_ind.get(ind.id), "escala_max": ind.escala_max}
                for ind in indicadores_act
            ]
        puntos_maximos += max_act
        puntos_obtenidos += obt_act
        pct_act = (obt_act / max_act * Decimal("100")) if max_act > 0 else Decimal("0")
        detalle.append({
            "actividad": act,
            "maximo": max_act,
            "obtenido": obt_act,
            "porcentaje_logro": pct_act,
            "detalle_indicadores": detalle_indicadores,
        })

    pct_logro = (puntos_obtenidos / puntos_maximos * Decimal("100")) if puntos_maximos > 0 else Decimal("0")
    pct_comp = obtener_porcentaje_componente_esquema(asignacion, tipo_componente)
    aporte = (pct_logro / Decimal("100")) * pct_comp

    return {
        "puntos_obtenidos": puntos_obtenidos,
        "puntos_maximos": puntos_maximos,
        "porcentaje_logro": pct_logro,
        "porcentaje_componente": pct_comp,
        "aporte": aporte,
        "detalle_actividades": detalle,
    }


def calcular_resumen_evaluacion_completo(asignacion, periodo_id, matriculas):
    """
    Resumen por estudiante con TAREAS y COTIDIANOS.
    Retorna lista de dicts con estudiante y datos por componente.
    Optimizado: prefetch actividades e indicadores, una query de puntajes por tipo.
    """
    est_ids = [m.estudiante_id for m in matriculas]
    if not est_ids:
        return []

    def _resumen_por_tipo(tipo_componente):
        es_simple = tipo_componente in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO)
        actividades = list(
            ActividadEvaluacion.objects.filter(
                docente_asignacion=asignacion,
                periodo_id=periodo_id,
                tipo_componente=tipo_componente,
                estado__in=ACTIVIDADES_ACUMULADO_ESTADOS,
            )
            .prefetch_related("indicadores")
            .order_by("titulo")
        )
        act_max = {}  # actividad_id -> max
        obt_por_est_act = {}  # (est_id, act_id) -> sum
        if es_simple:
            for act in actividades:
                max_act = act.puntaje_total or Decimal("0")
                if max_act > 0:
                    act_max[act.id] = max_act
            puntajes_raw = list(
                PuntajeSimple.objects.filter(
                    actividad_id__in=list(act_max.keys()),
                    estudiante_id__in=est_ids,
                )
                .exclude(puntos_obtenidos__isnull=True)
                .values("actividad_id", "estudiante_id", "puntos_obtenidos")
            )
            for p in puntajes_raw:
                key = (p["estudiante_id"], p["actividad_id"])
                obt_por_est_act[key] = p["puntos_obtenidos"]
        else:
            act_ind_ids = {}  # actividad_id -> [ind_ids]
            for act in actividades:
                inds = [i for i in act.indicadores.all() if i.activo]
                if not inds:
                    continue
                act_ind_ids[act.id] = [i.id for i in inds]
                act_max[act.id] = sum(i.escala_max for i in inds)

            ind_ids_flat = [iid for ids in act_ind_ids.values() for iid in ids]
            puntajes_raw = (
                list(
                    PuntajeIndicador.objects.filter(
                        indicador_id__in=ind_ids_flat,
                        estudiante_id__in=est_ids,
                    )
                    .exclude(puntaje_obtenido__isnull=True)
                    .values("indicador_id", "estudiante_id", "puntaje_obtenido")
                )
                if ind_ids_flat
                else []
            )

            ind_to_act = {}
            for act_id, ind_ids in act_ind_ids.items():
                for iid in ind_ids:
                    ind_to_act[iid] = act_id

            for p in puntajes_raw:
                act_id = ind_to_act.get(p["indicador_id"])
                if act_id:
                    key = (p["estudiante_id"], act_id)
                    obt_por_est_act[key] = obt_por_est_act.get(key, Decimal("0")) + p["puntaje_obtenido"]

        pct_comp = obtener_porcentaje_componente_esquema(asignacion, tipo_componente)
        resumen = {}
        for est_id in est_ids:
            puntos_obt = Decimal("0")
            puntos_max = Decimal("0")
            for act_id, max_act in act_max.items():
                puntos_max += max_act
                puntos_obt += obt_por_est_act.get((est_id, act_id), Decimal("0"))
            pct_logro = (puntos_obt / puntos_max * Decimal("100")) if puntos_max > 0 else Decimal("0")
            aporte = (pct_logro / Decimal("100")) * pct_comp
            resumen[est_id] = {
                "puntos_obtenidos": puntos_obt,
                "puntos_maximos": puntos_max,
                "porcentaje_logro": pct_logro,
                "porcentaje_componente": pct_comp,
                "aporte": aporte,
                "detalle_actividades": [],  # no usado en grilla principal
            }
        return resumen

    resumen_tareas = _resumen_por_tipo(ActividadEvaluacion.TAREA)
    resumen_cotidianos = _resumen_por_tipo(ActividadEvaluacion.COTIDIANO)
    resumen_pruebas = _resumen_por_tipo(ActividadEvaluacion.PRUEBA)
    resumen_proyectos = _resumen_por_tipo(ActividadEvaluacion.PROYECTO)

    filas = []
    for m in matriculas:
        est = m.estudiante
        filas.append({
            "matricula": m,
            "estudiante": est,
            "tareas": resumen_tareas.get(est.id, {}),
            "cotidianos": resumen_cotidianos.get(est.id, {}),
            "pruebas": resumen_pruebas.get(est.id, {}),
            "proyectos": resumen_proyectos.get(est.id, {}),
        })
    return filas


def porcentaje_disponible_para_tipo(asignacion, periodo_id, tipo_componente, actividad_excluir_id=None):
    """
    Retorna cuánto porcentaje queda disponible para crear/editar una actividad
    PRUEBA/PROYECTO en el periodo sin exceder lo definido en esquema.
    """
    pct_esquema = obtener_porcentaje_componente_esquema(asignacion, tipo_componente) or Decimal("0")
    qs = ActividadEvaluacion.objects.filter(
        docente_asignacion=asignacion,
        periodo_id=periodo_id,
        tipo_componente=tipo_componente,
    )
    if actividad_excluir_id:
        qs = qs.exclude(id=actividad_excluir_id)
    usado = qs.aggregate(s=Sum("porcentaje_actividad"))["s"] or Decimal("0")
    return pct_esquema - usado, pct_esquema, usado


def actividad_pertenece_a_institucion(actividad, institucion_id):
    """
    Verifica que la actividad pertenezca a la institución indicada.
    """
    if not actividad or not institucion_id:
        return False
    return actividad.institucion_id == institucion_id


def duplicar_actividad(actividad_origen, titulo_nuevo=None):
    """
    Duplica una actividad.
    Si es TAREA/COTIDIANO copia indicadores; si es PRUEBA/PROYECTO copia valores simples.
    NO copia puntajes de estudiantes.
    Devuelve la nueva actividad.
    """
    from django.db import transaction

    with transaction.atomic():
        nueva = ActividadEvaluacion.objects.create(
            docente_asignacion=actividad_origen.docente_asignacion,
            institucion=actividad_origen.institucion,
            curso_lectivo=actividad_origen.curso_lectivo,
            periodo=actividad_origen.periodo,
            tipo_componente=actividad_origen.tipo_componente,
            titulo=titulo_nuevo or f"Copia – {actividad_origen.titulo}",
            descripcion=actividad_origen.descripcion or "",
            puntaje_total=actividad_origen.puntaje_total,
            porcentaje_actividad=actividad_origen.porcentaje_actividad,
            fecha_asignacion=actividad_origen.fecha_asignacion,
            fecha_entrega=actividad_origen.fecha_entrega,
            estado=ActividadEvaluacion.BORRADOR,
            alcance_estudiantes=actividad_origen.alcance_estudiantes,
            created_by=actividad_origen.created_by,
        )
        if actividad_origen.tipo_componente not in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO):
            for ind in actividad_origen.indicadores.filter(activo=True).order_by("orden", "id"):
                IndicadorActividad.objects.create(
                    actividad=nueva,
                    orden=ind.orden,
                    descripcion=ind.descripcion,
                    escala_min=ind.escala_min,
                    escala_max=ind.escala_max,
                    activo=True,
                )
    return nueva


def copiar_actividad_a_asignaciones(actividad_origen, asignacion_ids, created_by=None):
    """
    Copia una actividad (datos + indicadores) a otras asignaciones.
    NO copia puntajes. Cada asignación destino debe tener el mismo periodo disponible.
    Retorna lista de actividades creadas.
    """
    from django.db import transaction
    from evaluaciones.models import DocenteAsignacion, PeriodoCursoLectivo

    periodo = actividad_origen.periodo
    inst_id = actividad_origen.institucion_id
    curso_lectivo_id = actividad_origen.curso_lectivo_id
    subarea_id = actividad_origen.docente_asignacion.subarea_curso.subarea_id

    asignaciones = list(
        DocenteAsignacion.objects.select_related("subarea_curso").filter(
            id__in=asignacion_ids,
            activo=True,
            subarea_curso__institucion_id=inst_id,
            subarea_curso__subarea_id=subarea_id,
            curso_lectivo_id=curso_lectivo_id,
        )
    )

    creadas = []
    with transaction.atomic():
        es_simple = actividad_origen.tipo_componente in (ActividadEvaluacion.PRUEBA, ActividadEvaluacion.PROYECTO)
        indicadores = list(actividad_origen.indicadores.filter(activo=True).order_by("orden", "id"))
        for da in asignaciones:
            # Verificar periodo para esta asignación (mismo curso_lectivo)
            pcl = PeriodoCursoLectivo.objects.filter(
                institucion_id=da.subarea_curso.institucion_id,
                curso_lectivo_id=da.curso_lectivo_id,
                periodo=periodo,
                activo=True,
            ).first()
            if not pcl:
                continue
            if es_simple:
                pct_esquema = obtener_porcentaje_componente_esquema(
                    da, actividad_origen.tipo_componente
                ) or Decimal("0")
                pct_actividad = actividad_origen.porcentaje_actividad or Decimal("0")
                if pct_esquema <= 0:
                    continue
                usado = (
                    ActividadEvaluacion.objects.filter(
                        docente_asignacion=da,
                        periodo=periodo,
                        tipo_componente=actividad_origen.tipo_componente,
                    ).aggregate(s=Sum("porcentaje_actividad"))["s"] or Decimal("0")
                )
                if usado + pct_actividad > pct_esquema:
                    continue
            nueva = ActividadEvaluacion.objects.create(
                docente_asignacion=da,
                institucion=da.subarea_curso.institucion,
                curso_lectivo=da.curso_lectivo,
                periodo=periodo,
                tipo_componente=actividad_origen.tipo_componente,
                titulo=actividad_origen.titulo,
                descripcion=actividad_origen.descripcion or "",
                puntaje_total=actividad_origen.puntaje_total,
                porcentaje_actividad=actividad_origen.porcentaje_actividad,
                fecha_asignacion=actividad_origen.fecha_asignacion,
                fecha_entrega=actividad_origen.fecha_entrega,
                estado=ActividadEvaluacion.BORRADOR,
                alcance_estudiantes=actividad_origen.alcance_estudiantes,
                created_by=created_by or actividad_origen.created_by,
            )
            if not es_simple:
                for ind in indicadores:
                    IndicadorActividad.objects.create(
                        actividad=nueva,
                        orden=ind.orden,
                        descripcion=ind.descripcion,
                        escala_min=ind.escala_min,
                        escala_max=ind.escala_max,
                        activo=True,
                    )
            creadas.append(nueva)
    return creadas
