import base64
import io
from datetime import datetime, timedelta

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from catalogos.models import CursoLectivo
from core.models import Institucion
from matricula.models import MatriculaAcademica

from .models import (
    BecaComedor,
    ConfiguracionComedor,
    RegistroAlmuerzo,
    RegistroAlmuerzoTiquete,
    TiqueteComedor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolver_institucion(request, institucion_param=None):
    if request.user.is_superuser:
        if not institucion_param:
            return None
        return Institucion.objects.filter(pk=institucion_param).first()

    institucion_id = getattr(request, "institucion_activa_id", None)
    if not institucion_id:
        return None
    return Institucion.objects.filter(pk=institucion_id).first()


def _qr_base64(texto):
    """Genera un QR y lo devuelve como string base64 para usar en <img src>."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(texto)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# Registrar beca
# ---------------------------------------------------------------------------

@login_required
@permission_required("comedor.access_registro_beca_comedor", raise_exception=True)
def registrar_beca_comedor(request):
    from config_institucional.models import Nivel

    todos_cursos = CursoLectivo.objects.all().order_by("-anio")
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []
    niveles = Nivel.objects.all().order_by("numero")
    error = ""

    curso_lectivo_id = (
        request.POST.get("curso_lectivo_id") or request.GET.get("curso_lectivo_id") or ""
    ).strip()

    if request.user.is_superuser:
        if curso_lectivo_id:
            curso_lectivo = CursoLectivo.objects.filter(pk=curso_lectivo_id).first()
        else:
            curso_lectivo = CursoLectivo.get_activo() or todos_cursos.first()
            if curso_lectivo:
                curso_lectivo_id = str(curso_lectivo.pk)
    else:
        curso_lectivo = CursoLectivo.get_activo()
        if curso_lectivo:
            curso_lectivo_id = str(curso_lectivo.pk)
        else:
            error = "No existe un curso lectivo activo."

    institucion_param = request.POST.get("institucion") if request.method == "POST" else request.GET.get("institucion")
    institucion = _resolver_institucion(request, institucion_param)

    if not request.user.is_superuser and not institucion:
        error = "No se pudo determinar la institución activa."

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


# ---------------------------------------------------------------------------
# Almuerzo (beca + tiquete)
# ---------------------------------------------------------------------------

@login_required
@permission_required("comedor.access_almuerzo_comedor", raise_exception=True)
def almuerzo_comedor(request):
    curso_lectivo = CursoLectivo.get_activo()
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []

    if request.method == "POST":
        institucion = _resolver_institucion(request, request.POST.get("institucion"))
        entrada = (request.POST.get("identificacion") or "").strip().upper()

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
        if not entrada:
            return JsonResponse(
                {"ok": False, "status": "error", "message": "Debe ingresar una identificación o código."},
                status=400,
            )

        config = ConfiguracionComedor.objects.filter(institucion=institucion).first()
        intervalo_minutos = config.intervalo_minutos if config else 1200
        desde = timezone.now() - timedelta(minutes=intervalo_minutos)

        # ── 1. Intentar como identificación de estudiante ──────────────────
        matricula = (
            MatriculaAcademica.objects.filter(
                curso_lectivo=curso_lectivo,
                institucion=institucion,
                estado__iexact=MatriculaAcademica.ACTIVO,
                estudiante__identificacion=entrada,
            )
            .select_related("estudiante")
            .first()
        )

        if matricula:
            nombre = str(matricula.estudiante)

            beca_activa = BecaComedor.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
                estudiante=matricula.estudiante,
                activa=True,
            ).exists()

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
                mins_transcurridos = int(
                    (timezone.now() - registro_reciente.fecha_hora).total_seconds() / 60
                )
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
            )

            return JsonResponse(
                {
                    "ok": True,
                    "status": "ok",
                    "message": f"{nombre} registrado correctamente.",
                    "nombre": nombre,
                    "identificacion": matricula.estudiante.identificacion,
                    "tipo_acceso": "Alumno becado",
                }
            )

        # ── 2. Intentar como código de tiquete ─────────────────────────────
        tiquete = TiqueteComedor.objects.filter(
            codigo=entrada,
            institucion=institucion,
        ).first()

        if not tiquete:
            return JsonResponse(
                {
                    "ok": True,
                    "status": "no_encontrado",
                    "message": f"El código «{entrada}» no corresponde a ningún estudiante con beca ni a un tiquete.",
                    "identificacion": entrada,
                }
            )

        if not tiquete.activo:
            return JsonResponse(
                {
                    "ok": True,
                    "status": "inactivo",
                    "message": f"El tiquete {entrada} está inactivo.",
                    "identificacion": entrada,
                }
            )

        registro_reciente_tiq = (
            RegistroAlmuerzoTiquete.objects.filter(
                tiquete=tiquete,
                fecha_hora__gte=desde,
            )
            .order_by("-fecha_hora")
            .first()
        )

        if registro_reciente_tiq:
            mins_transcurridos = int(
                (timezone.now() - registro_reciente_tiq.fecha_hora).total_seconds() / 60
            )
            mins_restantes = intervalo_minutos - mins_transcurridos
            return JsonResponse(
                {
                    "ok": True,
                    "status": "duplicado",
                    "message": (
                        f"{tiquete.get_tipo_display()} ya registró a las "
                        f"{registro_reciente_tiq.fecha_hora:%H:%M}. "
                        f"Debe esperar {mins_restantes} minuto(s) más."
                    ),
                    "nombre": tiquete.get_tipo_display(),
                    "identificacion": tiquete.codigo,
                }
            )

        RegistroAlmuerzoTiquete.objects.create(
            institucion=institucion,
            curso_lectivo=curso_lectivo,
            tiquete=tiquete,
            fecha=timezone.localdate(),
        )

        return JsonResponse(
            {
                "ok": True,
                "status": "ok",
                "message": f"{tiquete.get_tipo_display()} registrado correctamente.",
                "nombre": tiquete.get_tipo_display(),
                "identificacion": tiquete.codigo,
                "tipo_acceso": tiquete.get_tipo_display(),
            }
        )

    institucion = _resolver_institucion(request, request.GET.get("institucion"))
    config = ConfiguracionComedor.objects.filter(institucion=institucion).first() if institucion else None
    intervalo_minutos = config.intervalo_minutos if config else 1200

    context = {
        "curso_lectivo": curso_lectivo,
        "instituciones": instituciones,
        "institucion": institucion,
        "es_superusuario": request.user.is_superuser,
        "intervalo_minutos": intervalo_minutos,
        "intervalo_horas": round(intervalo_minutos / 60, 1),
    }
    return render(request, "comedor/almuerzo.html", context)


# ---------------------------------------------------------------------------
# Gestionar tiquetes
# ---------------------------------------------------------------------------

@login_required
@permission_required("comedor.access_tiquetes_comedor", raise_exception=True)
def gestionar_tiquetes(request):
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []
    institucion_param = request.POST.get("institucion") if request.method == "POST" else request.GET.get("institucion")
    institucion = _resolver_institucion(request, institucion_param)

    error = ""
    if not institucion:
        if request.user.is_superuser:
            error = "Seleccione una institución."
        else:
            error = "No se pudo determinar la institución activa."

    if request.method == "POST" and request.POST.get("accion") == "crear_lote" and institucion:
        tipo = request.POST.get("tipo", "").strip()
        monto_raw = request.POST.get("monto", "0").strip()
        cantidad_raw = request.POST.get("cantidad", "1").strip()

        if tipo not in (TiqueteComedor.ALUMNO_TIQ, TiqueteComedor.PROFESOR):
            messages.error(request, "Tipo de tiquete no válido.")
        else:
            try:
                monto = float(monto_raw)
                cantidad = int(cantidad_raw)
                if cantidad < 1 or cantidad > 500:
                    raise ValueError("Cantidad fuera de rango")
            except (ValueError, TypeError):
                messages.error(request, "Monto o cantidad no válidos (máximo 500 por lote).")
            else:
                creados = 0
                for _ in range(cantidad):
                    TiqueteComedor.objects.create(
                        tipo=tipo,
                        monto=monto,
                        activo=True,
                        institucion=institucion,
                        created_by=request.user,
                    )
                    creados += 1
                messages.success(request, f"Se crearon {creados} tiquetes correctamente.")

    # Filtros de lista
    filtro_tipo = request.GET.get("filtro_tipo", "")
    filtro_estado = request.GET.get("filtro_estado", "")
    filtro_codigo = request.GET.get("filtro_codigo", "").strip().upper()

    tiquetes_qs = TiqueteComedor.objects.all()
    if institucion:
        tiquetes_qs = tiquetes_qs.filter(institucion=institucion)
    if filtro_tipo:
        tiquetes_qs = tiquetes_qs.filter(tipo=filtro_tipo)
    if filtro_estado == "activo":
        tiquetes_qs = tiquetes_qs.filter(activo=True)
    elif filtro_estado == "inactivo":
        tiquetes_qs = tiquetes_qs.filter(activo=False)
    if filtro_codigo:
        tiquetes_qs = tiquetes_qs.filter(codigo__icontains=filtro_codigo)

    tiquetes_qs = tiquetes_qs.select_related("institucion", "created_by").order_by("tipo", "codigo")

    context = {
        "instituciones": instituciones,
        "institucion": institucion,
        "es_superusuario": request.user.is_superuser,
        "tiquetes": tiquetes_qs,
        "tipos": TiqueteComedor.TIPO_CHOICES,
        "filtro_tipo": filtro_tipo,
        "filtro_estado": filtro_estado,
        "filtro_codigo": filtro_codigo,
        "error": error,
    }
    return render(request, "comedor/tiquetes.html", context)


@login_required
@permission_required("comedor.access_tiquetes_comedor", raise_exception=True)
def toggle_tiquete(request, tiquete_id):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)

    institucion = _resolver_institucion(request, request.POST.get("institucion"))
    tiquete = get_object_or_404(TiqueteComedor, pk=tiquete_id)

    if not request.user.is_superuser and tiquete.institucion != institucion:
        return JsonResponse({"ok": False, "message": "Sin permiso."}, status=403)

    tiquete.activo = not tiquete.activo
    tiquete.save(update_fields=["activo"])
    return JsonResponse({"ok": True, "activo": tiquete.activo})


# ---------------------------------------------------------------------------
# Imprimir tiquetes (QR)
# ---------------------------------------------------------------------------

@login_required
@permission_required("comedor.access_tiquetes_comedor", raise_exception=True)
def imprimir_tiquetes(request):
    institucion = _resolver_institucion(request, request.GET.get("institucion"))
    instituciones = Institucion.objects.all().order_by("nombre") if request.user.is_superuser else []

    ids_raw = request.GET.get("ids", "")
    filtro_tipo = request.GET.get("tipo", "")
    por_hoja = int(request.GET.get("por_hoja", 9))

    if ids_raw:
        ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]
        tiquetes_qs = TiqueteComedor.objects.filter(pk__in=ids)
    else:
        tiquetes_qs = TiqueteComedor.objects.filter(activo=True)
        if institucion:
            tiquetes_qs = tiquetes_qs.filter(institucion=institucion)
        if filtro_tipo:
            tiquetes_qs = tiquetes_qs.filter(tipo=filtro_tipo)

    tiquetes_con_qr = []
    for t in tiquetes_qs.order_by("tipo", "codigo"):
        tiquetes_con_qr.append({
            "tiquete": t,
            "qr_b64": _qr_base64(t.codigo),
        })

    context = {
        "tiquetes_con_qr": tiquetes_con_qr,
        "por_hoja": por_hoja,
        "instituciones": instituciones,
        "institucion": institucion,
        "es_superusuario": request.user.is_superuser,
        "tipos": TiqueteComedor.TIPO_CHOICES,
        "filtro_tipo": filtro_tipo,
        "ids_raw": ids_raw,
    }
    return render(request, "comedor/imprimir_tiquetes.html", context)


# ---------------------------------------------------------------------------
# Reportes
# ---------------------------------------------------------------------------

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
    total_registros_beca = 0
    total_estudiantes_unicos = 0
    por_dia = []
    becados_sin_uso = []

    total_tiquetes_activos = 0
    total_usos_tiquete = 0
    usos_por_tipo_tiquete = []
    por_dia_tiquete = []

    if curso_lectivo and institucion:
        # ── Becas ────────────────────────────────────────────────────────────
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

        registros_beca_qs = RegistroAlmuerzo.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_lectivo,
            fecha__range=(fecha_inicio, fecha_fin),
        )
        total_registros_beca = registros_beca_qs.count()
        total_estudiantes_unicos = registros_beca_qs.values("estudiante_id").distinct().count()

        por_dia = list(
            registros_beca_qs.values("fecha")
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

        # ── Tiquetes ─────────────────────────────────────────────────────────
        total_tiquetes_activos = TiqueteComedor.objects.filter(
            institucion=institucion, activo=True
        ).count()

        registros_tiq_qs = RegistroAlmuerzoTiquete.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_lectivo,
            fecha__range=(fecha_inicio, fecha_fin),
        )
        total_usos_tiquete = registros_tiq_qs.count()

        usos_por_tipo_tiquete = list(
            registros_tiq_qs.values("tiquete__tipo")
            .annotate(total=Count("id"))
            .order_by("tiquete__tipo")
        )
        # Añadir label legible
        tipo_labels = dict(TiqueteComedor.TIPO_CHOICES)
        for item in usos_por_tipo_tiquete:
            item["tipo_display"] = tipo_labels.get(item["tiquete__tipo"], item["tiquete__tipo"])

        por_dia_tiquete = list(
            registros_tiq_qs.values("fecha", "tiquete__tipo")
            .annotate(total=Count("id"))
            .order_by("fecha", "tiquete__tipo")
        )
        for item in por_dia_tiquete:
            item["tipo_display"] = tipo_labels.get(item["tiquete__tipo"], item["tiquete__tipo"])

    contexto = {
        "curso_lectivo": curso_lectivo,
        "instituciones": instituciones,
        "institucion": institucion,
        "es_superusuario": request.user.is_superuser,
        "periodo": periodo,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        # becas
        "total_becados": total_becados,
        "total_registros": total_registros_beca,
        "total_estudiantes_unicos": total_estudiantes_unicos,
        "por_dia": por_dia,
        "becados_sin_uso": becados_sin_uso,
        # tiquetes
        "total_tiquetes_activos": total_tiquetes_activos,
        "total_usos_tiquete": total_usos_tiquete,
        "usos_por_tipo_tiquete": usos_por_tipo_tiquete,
        "por_dia_tiquete": por_dia_tiquete,
    }
    return render(request, "comedor/reportes.html", contexto)
