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

from .models import BecaComedor, RegistroAlmuerzo


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
    curso_lectivo = CursoLectivo.get_activo()
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []
    data = request.POST if request.method == "POST" else request.GET
    institucion = _resolver_institucion(request, data.get("institucion"))

    filtros = {
        "cedula": (data.get("cedula") or "").strip().upper(),
        "nombre": (data.get("nombre") or "").strip(),
        "seccion": (data.get("seccion") or "").strip(),
        "subgrupo": (data.get("subgrupo") or "").strip(),
        "becado": (data.get("becado") or "").strip(),
    }

    matriculas_qs = MatriculaAcademica.objects.none()
    secciones = []
    subgrupos = []

    if curso_lectivo and institucion:
        base_qs = (
            MatriculaAcademica.objects.filter(
                curso_lectivo=curso_lectivo,
                institucion=institucion,
                estado__iexact=MatriculaAcademica.ACTIVO,
            )
            .select_related("estudiante", "nivel", "seccion", "subgrupo")
            .order_by(
                "estudiante__primer_apellido",
                "estudiante__segundo_apellido",
                "estudiante__nombres",
            )
        )

        secciones = (
            base_qs.exclude(seccion__isnull=True)
            .values_list("seccion__numero", flat=True)
            .distinct()
            .order_by("seccion__numero")
        )
        subgrupos = (
            base_qs.exclude(subgrupo__isnull=True)
            .values_list("subgrupo__letra", flat=True)
            .distinct()
            .order_by("subgrupo__letra")
        )

        if filtros["cedula"]:
            base_qs = base_qs.filter(estudiante__identificacion__icontains=filtros["cedula"])
        if filtros["nombre"]:
            base_qs = base_qs.filter(
                Q(estudiante__nombres__icontains=filtros["nombre"])
                | Q(estudiante__primer_apellido__icontains=filtros["nombre"])
                | Q(estudiante__segundo_apellido__icontains=filtros["nombre"])
            )
        if filtros["seccion"]:
            base_qs = base_qs.filter(seccion__numero=filtros["seccion"])
        if filtros["subgrupo"]:
            base_qs = base_qs.filter(subgrupo__letra=filtros["subgrupo"])

        becas_activas_ids = set(
            BecaComedor.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
                activa=True,
                estudiante_id__in=base_qs.values_list("estudiante_id", flat=True),
            ).values_list("estudiante_id", flat=True)
        )

        if filtros["becado"] == "si":
            base_qs = base_qs.filter(estudiante_id__in=becas_activas_ids)
        elif filtros["becado"] == "no":
            base_qs = base_qs.exclude(estudiante_id__in=becas_activas_ids)

        matriculas_qs = base_qs

        if request.method == "POST" and data.get("accion") == "guardar":
            ids_visibles = list(matriculas_qs.values_list("estudiante_id", flat=True))
            ids_marcados = {int(x) for x in request.POST.getlist("becados") if x.isdigit()}
            becas_existentes = {
                beca.estudiante_id: beca
                for beca in BecaComedor.objects.filter(
                    institucion=institucion,
                    curso_lectivo=curso_lectivo,
                    estudiante_id__in=ids_visibles,
                )
            }

            creadas = 0
            activadas = 0
            desactivadas = 0

            for estudiante_id in ids_visibles:
                debe_estar_activa = estudiante_id in ids_marcados
                beca = becas_existentes.get(estudiante_id)

                if beca:
                    if beca.activa != debe_estar_activa:
                        beca.activa = debe_estar_activa
                        beca.usuario_actualizacion = request.user
                        beca.save(update_fields=["activa", "usuario_actualizacion", "fecha_actualizacion"])
                        if debe_estar_activa:
                            activadas += 1
                        else:
                            desactivadas += 1
                elif debe_estar_activa:
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
                f"Proceso completado. Creadas: {creadas}, activadas: {activadas}, desactivadas: {desactivadas}.",
            )

            becas_activas_ids = set(
                BecaComedor.objects.filter(
                    institucion=institucion,
                    curso_lectivo=curso_lectivo,
                    activa=True,
                    estudiante_id__in=matriculas_qs.values_list("estudiante_id", flat=True),
                ).values_list("estudiante_id", flat=True)
            )

    page_number = request.GET.get("page") if request.method == "GET" else 1
    paginator = Paginator(list(matriculas_qs), 80)
    page_obj = paginator.get_page(page_number)
    becas_pagina_ids = set()
    if curso_lectivo and institucion and page_obj.object_list:
        becas_pagina_ids = set(
            BecaComedor.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
                activa=True,
                estudiante_id__in=[m.estudiante_id for m in page_obj.object_list],
            ).values_list("estudiante_id", flat=True)
        )

    context = {
        "curso_lectivo": curso_lectivo,
        "instituciones": instituciones,
        "institucion": institucion,
        "es_superusuario": request.user.is_superuser,
        "filtros": filtros,
        "secciones": secciones,
        "subgrupos": subgrupos,
        "page_obj": page_obj,
        "becas_pagina_ids": becas_pagina_ids,
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
                    "status": "no_beca",
                    "message": "El estudiante no tiene matrícula activa en el curso lectivo actual.",
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
        hoy = timezone.localdate()

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

        registro_existente = RegistroAlmuerzo.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_lectivo,
            estudiante=matricula.estudiante,
            fecha=hoy,
        ).first()

        if registro_existente:
            return JsonResponse(
                {
                    "ok": True,
                    "status": "duplicado",
                    "message": f"{nombre} ya registró almuerzo hoy a las {registro_existente.fecha_hora:%H:%M}.",
                    "nombre": nombre,
                    "identificacion": matricula.estudiante.identificacion,
                }
            )

        RegistroAlmuerzo.objects.create(
            institucion=institucion,
            curso_lectivo=curso_lectivo,
            estudiante=matricula.estudiante,
            fecha=hoy,
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
    context = {
        "curso_lectivo": curso_lectivo,
        "instituciones": instituciones,
        "institucion": institucion,
        "es_superusuario": request.user.is_superuser,
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

