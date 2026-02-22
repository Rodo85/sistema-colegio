from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from catalogos.models import CursoLectivo, SubArea
from core.models import Institucion

from .forms import DocenteAsignacionForm, PeriodoCursoLectivoForm, SubareaCursoLectivoForm
from .models import (
    DocenteAsignacion,
    EsquemaEval,
    Periodo,
    PeriodoCursoLectivo,
    SubareaCursoLectivo,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _resolver_institucion(request, param=None):
    if request.user.is_superuser:
        if not param:
            return None
        return Institucion.objects.filter(pk=param).first()
    iid = getattr(request, "institucion_activa_id", None)
    return Institucion.objects.filter(pk=iid).first() if iid else None


def _resolver_curso(param=None):
    if param:
        return CursoLectivo.objects.filter(pk=param).first()
    return CursoLectivo.get_activo()


# ─────────────────────────────────────────────────────────────────────────────
# Subáreas por Curso Lectivo
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@permission_required("evaluaciones.access_subareas_curso", raise_exception=True)
def gestion_subareas(request):
    todos_cursos = CursoLectivo.objects.all().order_by("-anio")
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []

    param_inst = request.POST.get("institucion") if request.method == "POST" else request.GET.get("institucion")
    param_cl = request.POST.get("curso_lectivo") if request.method == "POST" else request.GET.get("curso_lectivo")

    institucion = _resolver_institucion(request, param_inst)
    curso_lectivo = _resolver_curso(param_cl)

    error = ""
    if not institucion:
        error = "Seleccione una institución." if request.user.is_superuser else "No se pudo determinar la institución activa."

    subareas_activadas = []
    todas_subareas = []
    esquemas = EsquemaEval.objects.filter(activo=True).order_by("tipo", "nombre")

    if institucion and curso_lectivo:
        todas_subareas = list(SubArea.objects.all().order_by("nombre"))

        # Mapa de las ya configuradas
        conf_map = {
            s.subarea_id: s
            for s in SubareaCursoLectivo.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
            ).select_related("subarea", "eval_scheme")
        }

        subareas_activadas = [
            {
                "subarea": sa,
                "config": conf_map.get(sa.pk),
                "activa": conf_map[sa.pk].activa if sa.pk in conf_map else False,
            }
            for sa in todas_subareas
        ]

        if request.method == "POST" and request.POST.get("accion") == "guardar":
            ids_activados = set(
                int(x) for x in request.POST.getlist("activas") if x.isdigit()
            )
            esquema_por_subarea = {
                int(k.split("_")[1]): v
                for k, v in request.POST.items()
                if k.startswith("esquema_") and v
            }

            creadas = actualizadas = 0
            for sa in todas_subareas:
                debe_activa = sa.pk in ids_activados
                esquema_id = esquema_por_subarea.get(sa.pk) or None
                conf = conf_map.get(sa.pk)
                if conf:
                    cambio = conf.activa != debe_activa or str(conf.eval_scheme_id or "") != str(esquema_id or "")
                    if cambio:
                        conf.activa = debe_activa
                        conf.eval_scheme_id = esquema_id
                        conf.save(update_fields=["activa", "eval_scheme_id"])
                        actualizadas += 1
                else:
                    SubareaCursoLectivo.objects.create(
                        institucion=institucion,
                        curso_lectivo=curso_lectivo,
                        subarea=sa,
                        activa=debe_activa,
                        eval_scheme_id=esquema_id,
                    )
                    creadas += 1

            messages.success(request, f"Guardado. Nuevas: {creadas} | Actualizadas: {actualizadas}.")

            # Recargar mapa
            conf_map = {
                s.subarea_id: s
                for s in SubareaCursoLectivo.objects.filter(
                    institucion=institucion, curso_lectivo=curso_lectivo,
                ).select_related("subarea", "eval_scheme")
            }
            subareas_activadas = [
                {
                    "subarea": sa,
                    "config": conf_map.get(sa.pk),
                    "activa": conf_map[sa.pk].activa if sa.pk in conf_map else False,
                }
                for sa in todas_subareas
            ]

    context = {
        "todos_cursos": todos_cursos,
        "instituciones": instituciones,
        "institucion": institucion,
        "curso_lectivo": curso_lectivo,
        "es_superusuario": request.user.is_superuser,
        "subareas_activadas": subareas_activadas,
        "esquemas": esquemas,
        "error": error,
    }
    return render(request, "evaluaciones/subareas_curso.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# Períodos por Curso Lectivo
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@permission_required("evaluaciones.access_periodos_curso", raise_exception=True)
def gestion_periodos(request):
    todos_cursos = CursoLectivo.objects.all().order_by("-anio")
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []
    todos_periodos = Periodo.objects.all().order_by("numero")

    param_inst = request.POST.get("institucion") if request.method == "POST" else request.GET.get("institucion")
    param_cl = request.POST.get("curso_lectivo") if request.method == "POST" else request.GET.get("curso_lectivo")

    institucion = _resolver_institucion(request, param_inst)
    curso_lectivo = _resolver_curso(param_cl)

    error = ""
    if not institucion:
        error = "Seleccione una institución." if request.user.is_superuser else "No se pudo determinar la institución activa."

    periodo_configs = []

    if institucion and curso_lectivo:
        conf_map = {
            pc.periodo_id: pc
            for pc in PeriodoCursoLectivo.objects.filter(
                institucion=institucion, curso_lectivo=curso_lectivo
            ).select_related("periodo")
        }
        periodo_configs = [
            {"periodo": p, "config": conf_map.get(p.pk)}
            for p in todos_periodos
        ]

        if request.method == "POST" and request.POST.get("accion") == "guardar":
            ids_activos = set(int(x) for x in request.POST.getlist("activos") if x.isdigit())
            creadas = actualizadas = 0
            for p in todos_periodos:
                debe_activo = p.pk in ids_activos
                f_inicio = request.POST.get(f"fecha_inicio_{p.pk}") or None
                f_fin = request.POST.get(f"fecha_fin_{p.pk}") or None
                conf = conf_map.get(p.pk)
                if conf:
                    conf.activo = debe_activo
                    conf.fecha_inicio = f_inicio
                    conf.fecha_fin = f_fin
                    try:
                        conf.full_clean()
                        conf.save()
                        actualizadas += 1
                    except ValidationError as e:
                        messages.error(request, f"Período {p.nombre}: {e.message}")
                else:
                    try:
                        pc = PeriodoCursoLectivo(
                            institucion=institucion,
                            curso_lectivo=curso_lectivo,
                            periodo=p,
                            activo=debe_activo,
                            fecha_inicio=f_inicio,
                            fecha_fin=f_fin,
                        )
                        pc.full_clean()
                        pc.save()
                        creadas += 1
                    except ValidationError as e:
                        messages.error(request, f"Período {p.nombre}: {e.message}")

            messages.success(request, f"Guardado. Nuevos: {creadas} | Actualizados: {actualizadas}.")

            conf_map = {
                pc.periodo_id: pc
                for pc in PeriodoCursoLectivo.objects.filter(
                    institucion=institucion, curso_lectivo=curso_lectivo
                ).select_related("periodo")
            }
            periodo_configs = [
                {"periodo": p, "config": conf_map.get(p.pk)}
                for p in todos_periodos
            ]

    context = {
        "todos_cursos": todos_cursos,
        "instituciones": instituciones,
        "institucion": institucion,
        "curso_lectivo": curso_lectivo,
        "es_superusuario": request.user.is_superuser,
        "periodo_configs": periodo_configs,
        "error": error,
    }
    return render(request, "evaluaciones/periodos_curso.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# Asignaciones Docentes
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@permission_required("evaluaciones.access_docente_asignacion", raise_exception=True)
def gestion_docentes(request):
    todos_cursos = CursoLectivo.objects.all().order_by("-anio")
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []

    param_inst = request.GET.get("institucion")
    param_cl = request.GET.get("curso_lectivo")
    institucion = _resolver_institucion(request, param_inst)
    curso_lectivo = _resolver_curso(param_cl)

    error = ""
    if not institucion:
        error = "Seleccione una institución." if request.user.is_superuser else "No se pudo determinar la institución activa."

    asignaciones = []
    if institucion and curso_lectivo:
        asignaciones = list(
            DocenteAsignacion.objects.filter(
                subarea_curso__institucion=institucion,
                curso_lectivo=curso_lectivo,
            )
            .select_related(
                "docente__usuario",
                "subarea_curso__subarea",
                "seccion",
                "subgrupo",
                "eval_scheme_snapshot",
            )
            .order_by(
                "subarea_curso__subarea__nombre",
                "docente__usuario__last_name",
            )
        )

    context = {
        "todos_cursos": todos_cursos,
        "instituciones": instituciones,
        "institucion": institucion,
        "curso_lectivo": curso_lectivo,
        "es_superusuario": request.user.is_superuser,
        "asignaciones": asignaciones,
        "error": error,
    }
    return render(request, "evaluaciones/docentes.html", context)


@login_required
@permission_required("evaluaciones.access_docente_asignacion", raise_exception=True)
def crear_asignacion(request):
    todos_cursos = CursoLectivo.objects.all().order_by("-anio")
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []

    param_inst = request.POST.get("institucion") if request.method == "POST" else request.GET.get("institucion")
    param_cl = request.POST.get("curso_lectivo") if request.method == "POST" else request.GET.get("curso_lectivo")
    institucion = _resolver_institucion(request, param_inst)
    curso_lectivo = _resolver_curso(param_cl)

    form = DocenteAsignacionForm(
        request.POST or None,
        institucion=institucion,
        curso_lectivo=curso_lectivo,
    )

    if request.method == "POST" and form.is_valid():
        asignacion = form.save(commit=False)
        asignacion.curso_lectivo = curso_lectivo
        try:
            asignacion.full_clean()
            asignacion.save()
            messages.success(request, "Asignación creada correctamente.")
        except ValidationError as e:
            form.add_error(None, e)

    context = {
        "form": form,
        "todos_cursos": todos_cursos,
        "instituciones": instituciones,
        "institucion": institucion,
        "curso_lectivo": curso_lectivo,
        "es_superusuario": request.user.is_superuser,
        "accion": "Crear",
    }
    return render(request, "evaluaciones/asignacion_form.html", context)


@login_required
@permission_required("evaluaciones.access_docente_asignacion", raise_exception=True)
def editar_asignacion(request, asignacion_id):
    asignacion = get_object_or_404(DocenteAsignacion, pk=asignacion_id)
    institucion = asignacion.subarea_curso.institucion
    curso_lectivo = asignacion.curso_lectivo
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []
    todos_cursos = CursoLectivo.objects.all().order_by("-anio")

    if not request.user.is_superuser:
        inst_activa_id = getattr(request, "institucion_activa_id", None)
        if institucion.pk != inst_activa_id:
            messages.error(request, "No tiene permisos para editar esta asignación.")
            return render(request, "evaluaciones/asignacion_form.html", {"error": "Sin permisos."})

    form = DocenteAsignacionForm(
        request.POST or None,
        instance=asignacion,
        institucion=institucion,
        curso_lectivo=curso_lectivo,
    )

    if request.method == "POST" and form.is_valid():
        try:
            asig = form.save(commit=False)
            asig.full_clean()
            asig.save()
            messages.success(request, "Asignación actualizada correctamente.")
        except ValidationError as e:
            form.add_error(None, e)

    context = {
        "form": form,
        "asignacion": asignacion,
        "todos_cursos": todos_cursos,
        "instituciones": instituciones,
        "institucion": institucion,
        "curso_lectivo": curso_lectivo,
        "es_superusuario": request.user.is_superuser,
        "accion": "Editar",
    }
    return render(request, "evaluaciones/asignacion_form.html", context)


@login_required
@permission_required("evaluaciones.access_docente_asignacion", raise_exception=True)
def toggle_asignacion(request, asignacion_id):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    asignacion = get_object_or_404(DocenteAsignacion, pk=asignacion_id)
    if not request.user.is_superuser:
        inst_activa_id = getattr(request, "institucion_activa_id", None)
        if asignacion.subarea_curso.institucion_id != inst_activa_id:
            return JsonResponse({"ok": False, "message": "Sin permisos."}, status=403)
    asignacion.activo = not asignacion.activo
    asignacion.save(update_fields=["activo"])
    return JsonResponse({"ok": True, "activo": asignacion.activo})
