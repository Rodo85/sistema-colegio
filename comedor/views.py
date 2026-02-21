from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from catalogos.models import CursoLectivo
from core.models import Institucion
from matricula.models import MatriculaAcademica

from .models import BecaComedor, ConfiguracionComedor, RegistroAlmuerzo


def _resolver_institucion(request, institucion_param=None):
    if request.user.is_superuser:
        if not institucion_param:
            return None
        return Institucion.objects.filter(pk=institucion_param).first()

    institucion_id = getattr(request, "institucion_activa_id", None)
    if not institucion_id:
        return None
    return Institucion.objects.filter(pk=institucion_id).first()


@login_required
@permission_required("comedor.access_registro_beca_comedor", raise_exception=True)
def registrar_beca_comedor(request):
    from config_institucional.models import Nivel

    todos_cursos = CursoLectivo.objects.all().order_by("-anio")
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []
    niveles = Nivel.objects.all().order_by("numero")
    error = ""

    # Resolver curso lectivo: superadmin puede elegir cualquiera; normal usa el activo
    curso_lectivo_id = (
        request.POST.get("curso_lectivo_id") or request.GET.get("curso_lectivo_id") or ""
    ).strip()

    if request.user.is_superuser:
        if curso_lectivo_id:
            curso_lectivo = CursoLectivo.objects.filter(pk=curso_lectivo_id).first()
        else:
            # Pre-seleccionar el activo si existe, si no el primero disponible
            curso_lectivo = CursoLectivo.get_activo() or todos_cursos.first()
            if curso_lectivo:
                curso_lectivo_id = str(curso_lectivo.pk)
    else:
        curso_lectivo = CursoLectivo.get_activo()
        if curso_lectivo:
            curso_lectivo_id = str(curso_lectivo.pk)
        else:
            error = "No existe un curso lectivo activo."

    # Resolver institución
    institucion_param = request.POST.get("institucion") if request.method == "POST" else request.GET.get("institucion")
    institucion = _resolver_institucion(request, institucion_param)

    if not request.user.is_superuser and not institucion:
        error = "No se pudo determinar la institución activa."

    # Filtros de la pantalla de selección
    nivel_id    = (request.POST.get("nivel_id")    or request.GET.get("nivel_id")    or "").strip()
    seccion_id  = (request.POST.get("seccion_id")  or request.GET.get("seccion_id")  or "").strip()
    subgrupo_id = (request.POST.get("subgrupo_id") or request.GET.get("subgrupo_id") or "").strip()

    matriculas = []
    becas_ids = set()
    mostrar_tabla = False

    if not error and curso_lectivo and institucion and (seccion_id or subgrupo_id):
        filtros_qs = {
            "curso_lectivo": curso_lectivo,
            "institucion": institucion,
            "estado__iexact": MatriculaAcademica.ACTIVO,
        }
        if subgrupo_id:
            filtros_qs["subgrupo_id"] = subgrupo_id
        elif seccion_id:
            filtros_qs["seccion_id"] = seccion_id

        qs = (
            MatriculaAcademica.objects.filter(**filtros_qs)
            .select_related("estudiante", "seccion", "subgrupo", "nivel")
            .order_by(
                "estudiante__primer_apellido",
                "estudiante__segundo_apellido",
                "estudiante__nombres",
            )
        )
        matriculas = list(qs)
        mostrar_tabla = True

        ids_estudiantes = [m.estudiante_id for m in matriculas]
        becas_ids = set(
            BecaComedor.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
                activa=True,
                estudiante_id__in=ids_estudiantes,
            ).values_list("estudiante_id", flat=True)
        )

        if request.method == "POST" and request.POST.get("accion") == "guardar":
            ids_marcados = {int(x) for x in request.POST.getlist("becados") if x.isdigit()}
            becas_existentes = {
                beca.estudiante_id: beca
                for beca in BecaComedor.objects.filter(
                    institucion=institucion,
                    curso_lectivo=curso_lectivo,
                    estudiante_id__in=ids_estudiantes,
                )
            }
            creadas = activadas = desactivadas = 0

            for estudiante_id in ids_estudiantes:
                debe_activa = estudiante_id in ids_marcados
                beca = becas_existentes.get(estudiante_id)
                if beca:
                    if beca.activa != debe_activa:
                        beca.activa = debe_activa
                        beca.usuario_actualizacion = request.user
                        beca.save(update_fields=["activa", "usuario_actualizacion", "fecha_actualizacion"])
                        if debe_activa:
                            activadas += 1
                        else:
                            desactivadas += 1
                elif debe_activa:
                    BecaComedor.objects.create(
                        institucion=institucion,
                        curso_lectivo=curso_lectivo,
                        estudiante_id=estudiante_id,
                        activa=True,
                        usuario_asignacion=request.user,
                        usuario_actualizacion=request.user,
                    )
                    creadas += 1

            messages.success(
                request,
                f"Guardado. Becas nuevas: {creadas} | Activadas: {activadas} | Desactivadas: {desactivadas}.",
            )

            # Refrescar becas tras guardar
            becas_ids = set(
                BecaComedor.objects.filter(
                    institucion=institucion,
                    curso_lectivo=curso_lectivo,
                    activa=True,
                    estudiante_id__in=ids_estudiantes,
                ).values_list("estudiante_id", flat=True)
            )

    context = {
        "todos_cursos": todos_cursos,
        "curso_lectivo": curso_lectivo,
        "curso_lectivo_id": curso_lectivo_id,
        "instituciones": instituciones,
        "institucion": institucion,
        "niveles": niveles,
        "es_superusuario": request.user.is_superuser,
        "nivel_id": nivel_id,
        "seccion_id": seccion_id,
        "subgrupo_id": subgrupo_id,
        "matriculas": matriculas,
        "becas_ids": becas_ids,
        "mostrar_tabla": mostrar_tabla,
        "error": error,
    }
    return render(request, "comedor/registrar_beca.html", context)


@login_required
@permission_required("comedor.access_almuerzo_comedor", raise_exception=True)
def almuerzo_comedor(request):
    curso_lectivo = CursoLectivo.get_activo()
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []

    if request.method == "POST":
        institucion = _resolver_institucion(request, request.POST.get("institucion"))
        identificacion = (request.POST.get("identificacion") or "").strip().upper()

        if not curso_lectivo:
            return JsonResponse(
                {"ok": False, "status": "error", "message": "No hay curso lectivo activo."},
                status=400,
            )
        if not institucion:
            return JsonResponse(
                {"ok": False, "status": "error", "message": "Debe seleccionar una institución válida."},
                status=400,
            )
        if not identificacion:
            return JsonResponse(
                {"ok": False, "status": "error", "message": "Debe ingresar una identificación."},
                status=400,
            )

        # Obtener configuración de intervalo para esta institución
        config = ConfiguracionComedor.objects.filter(institucion=institucion).first()
        intervalo_minutos = config.intervalo_minutos if config else 1200

        matricula = (
            MatriculaAcademica.objects.filter(
                curso_lectivo=curso_lectivo,
                institucion=institucion,
                estado__iexact=MatriculaAcademica.ACTIVO,
                estudiante__identificacion=identificacion,
            )
            .select_related("estudiante")
            .first()
        )

        if not matricula:
            return JsonResponse(
                {
                    "ok": True,
                    "status": "sin_matricula",
                    "message": f"Identificación {identificacion} no tiene matrícula activa en este curso lectivo.",
                    "identificacion": identificacion,
                }
            )

        beca_activa = BecaComedor.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_lectivo,
            estudiante=matricula.estudiante,
            activa=True,
        ).exists()

        nombre = str(matricula.estudiante)

        if not beca_activa:
            return JsonResponse(
                {
                    "ok": True,
                    "status": "no_beca",
                    "message": f"{nombre} no tiene beca de comedor.",
                    "nombre": nombre,
                    "identificacion": matricula.estudiante.identificacion,
                }
            )

        # Verificar si ya registró dentro del intervalo configurado
        desde = timezone.now() - timedelta(minutes=intervalo_minutos)
        registro_reciente = (
            RegistroAlmuerzo.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
                estudiante=matricula.estudiante,
                fecha_hora__gte=desde,
            )
            .order_by("-fecha_hora")
            .first()
        )

        if registro_reciente:
            mins_transcurridos = int((timezone.now() - registro_reciente.fecha_hora).total_seconds() / 60)
            mins_restantes = intervalo_minutos - mins_transcurridos
            return JsonResponse(
                {
                    "ok": True,
                    "status": "duplicado",
                    "message": (
                        f"{nombre} ya registró a las {registro_reciente.fecha_hora:%H:%M}. "
                        f"Debe esperar {mins_restantes} minuto(s) más."
                    ),
                    "nombre": nombre,
                    "identificacion": matricula.estudiante.identificacion,
                }
            )

        RegistroAlmuerzo.objects.create(
            institucion=institucion,
            curso_lectivo=curso_lectivo,
            estudiante=matricula.estudiante,
            fecha=timezone.localdate(),
            usuario_registro=request.user,
            observacion="Registro por lector QR",
        )

        return JsonResponse(
            {
                "ok": True,
                "status": "ok",
                "message": f"{nombre} registrado correctamente.",
                "nombre": nombre,
                "identificacion": matricula.estudiante.identificacion,
            }
        )

    institucion = _resolver_institucion(request, request.GET.get("institucion"))
    # Configuración de intervalo para mostrar en pantalla
    config = None
    if institucion:
        config = ConfiguracionComedor.objects.filter(institucion=institucion).first()

    context = {
        "curso_lectivo": curso_lectivo,
        "instituciones": instituciones,
        "institucion": institucion,
        "es_superusuario": request.user.is_superuser,
        "intervalo_minutos": config.intervalo_minutos if config else 1200,
    }
    return render(request, "comedor/almuerzo.html", context)


@login_required
@permission_required("comedor.access_reportes_comedor", raise_exception=True)
def reportes_comedor(request):
    curso_lectivo = CursoLectivo.get_activo()
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []
    institucion = _resolver_institucion(request, request.GET.get("institucion"))

    hoy = timezone.localdate()
    periodo = request.GET.get("periodo", "mes")
    fecha_inicio_txt = request.GET.get("fecha_inicio")
    fecha_fin_txt = request.GET.get("fecha_fin")

    if periodo == "dia":
        fecha_inicio = hoy
        fecha_fin = hoy
    elif periodo == "semana":
        fecha_inicio = hoy - timedelta(days=hoy.weekday())
        fecha_fin = hoy
    elif periodo == "rango" and fecha_inicio_txt and fecha_fin_txt:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_txt, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin_txt, "%Y-%m-%d").date()
            if fecha_inicio > fecha_fin:
                fecha_inicio, fecha_fin = fecha_fin, fecha_inicio
        except ValueError:
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = hoy
    else:
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = hoy
        periodo = "mes"

    total_becados = 0
    total_registros = 0
    total_estudiantes_unicos = 0
    por_dia = []
    becados_sin_uso = []

    if curso_lectivo and institucion:
        becas_qs = (
            BecaComedor.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
                activa=True,
                estudiante__matriculas_academicas__curso_lectivo=curso_lectivo,
                estudiante__matriculas_academicas__institucion=institucion,
                estudiante__matriculas_academicas__estado__iexact=MatriculaAcademica.ACTIVO,
            )
            .select_related("estudiante")
            .distinct()
        )
        total_becados = becas_qs.count()

        registros_qs = RegistroAlmuerzo.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_lectivo,
            fecha__range=(fecha_inicio, fecha_fin),
        )

        total_registros = registros_qs.count()
        total_estudiantes_unicos = registros_qs.values("estudiante_id").distinct().count()

        por_dia = list(
            registros_qs.values("fecha")
            .annotate(
                total_registros=Count("id"),
                total_estudiantes=Count("estudiante_id", distinct=True),
            )
            .order_by("fecha")
        )

        becados_sin_uso = list(
            becas_qs.exclude(
                estudiante__registros_almuerzo__institucion=institucion,
                estudiante__registros_almuerzo__curso_lectivo=curso_lectivo,
                estudiante__registros_almuerzo__fecha__range=(fecha_inicio, fecha_fin),
            )
            .order_by(
                "estudiante__primer_apellido",
                "estudiante__segundo_apellido",
                "estudiante__nombres",
            )[:250]
        )

    contexto = {
        "curso_lectivo": curso_lectivo,
        "instituciones": instituciones,
        "institucion": institucion,
        "es_superusuario": request.user.is_superuser,
        "periodo": periodo,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "total_becados": total_becados,
        "total_registros": total_registros,
        "total_estudiantes_unicos": total_estudiantes_unicos,
        "por_dia": por_dia,
        "becados_sin_uso": becados_sin_uso,
    }
    return render(request, "comedor/reportes.html", contexto)

