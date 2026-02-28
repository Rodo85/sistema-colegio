from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Permission
from datetime import timedelta

from core.models import Institucion
from config_institucional.models import Profesor
from core.forms import RegistroUsuarioForm
from core.models import Miembro, SolicitudRegistro, User


def _get_or_create_institucion_general():
    correo_base = "INSTITUCION.GENERAL@COLESMART.LOCAL"
    correo = correo_base
    n = 1
    while Institucion.objects.filter(correo=correo).exclude(es_institucion_general=True).exists():
        correo = f"INSTITUCION.GENERAL+{n}@COLESMART.LOCAL"
        n += 1

    defaults = {
        "correo": correo,
        "telefono": "",
        "direccion": "N/A",
        "tipo": Institucion.ACADEMICO,
        "fecha_inicio": timezone.now().date(),
        "fecha_fin": timezone.now().date() + timedelta(days=3650),
        "matricula_activa": False,
        "es_institucion_general": True,
        "max_asignaciones_general": 10,
    }
    institucion, created = Institucion.objects.get_or_create(
        es_institucion_general=True,
        defaults={"nombre": "INSTITUCION GENERAL", **defaults},
    )
    if created:
        return institucion
    changes = {}
    if not institucion.matricula_activa:
        pass
    else:
        changes["matricula_activa"] = False
    if institucion.nombre != "INSTITUCION GENERAL":
        changes["nombre"] = "INSTITUCION GENERAL"
    if institucion.max_asignaciones_general <= 0:
        changes["max_asignaciones_general"] = 10
    if changes:
        for k, v in changes.items():
            setattr(institucion, k, v)
        institucion.save(update_fields=list(changes.keys()))
    return institucion


def _identificacion_auto_docente(user):
    base = f"AUTO{str(user.id).replace('-', '')[:12]}".upper()
    return base[:20]


def _notificar_estado_solicitud(solicitud, fue_aprobada):
    if not solicitud or not solicitud.usuario_id:
        return
    usuario = solicitud.usuario
    nombre = (usuario.full_name() or usuario.first_name or usuario.email).strip()
    asunto = "Actualización de tu solicitud - Sistema Colegio"
    if fue_aprobada:
        cuerpo = (
            f"Hola {nombre},\n\n"
            "Tu solicitud fue aprobada. Ya puedes iniciar sesión en el sistema.\n\n"
            "Saludos."
        )
    else:
        motivo = (solicitud.motivo_revision or "").strip()
        cuerpo = (
            f"Hola {nombre},\n\n"
            "Tu solicitud fue rechazada. Contacta al administrador si crees que es un error.\n"
        )
        if motivo:
            cuerpo += f"\nMotivo: {motivo}\n"
        cuerpo += "\nSaludos."
    try:
        send_mail(
            asunto,
            cuerpo,
            getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@colesmart.local"),
            [usuario.email],
            fail_silently=True,
        )
    except Exception:
        pass


@transaction.atomic
def aprobar_solicitud_registro(solicitud, revisado_por):
    if solicitud.pk:
        estado_actual = (
            SolicitudRegistro.objects.filter(pk=solicitud.pk)
            .values_list("estado", flat=True)
            .first()
        )
        if estado_actual == SolicitudRegistro.APROBADA:
            return
    elif solicitud.estado == SolicitudRegistro.APROBADA:
        return
    institucion = solicitud.institucion_solicitada
    if not institucion or not institucion.activa:
        institucion = _get_or_create_institucion_general()
    user = solicitud.usuario
    user.estado_solicitud = User.ESTADO_ACTIVA
    user.is_active = True
    user.is_staff = True
    user.save(update_fields=["estado_solicitud", "is_active", "is_staff"])

    miembro, _ = Miembro.objects.get_or_create(
        usuario=user,
        institucion=institucion,
        defaults={"rol": Miembro.DOCENTE},
    )
    if miembro.rol != Miembro.DOCENTE:
        miembro.rol = Miembro.DOCENTE
        miembro.save(update_fields=["rol"])

    perm_libro = Permission.objects.filter(
        codename="access_libro_docente",
        content_type__app_label="libro_docente",
    ).first()
    if perm_libro:
        user.user_permissions.add(perm_libro)

    Profesor.objects.get_or_create(
        institucion=institucion,
        usuario=user,
        defaults={"identificacion": _identificacion_auto_docente(user), "telefono": ""},
    )

    solicitud.estado = SolicitudRegistro.APROBADA
    solicitud.revisado_por = revisado_por
    solicitud.fecha_revision = timezone.now()
    solicitud.motivo_revision = ""
    solicitud.save(
        update_fields=["estado", "revisado_por", "fecha_revision", "motivo_revision"]
    )
    _notificar_estado_solicitud(solicitud, fue_aprobada=True)


@transaction.atomic
def rechazar_solicitud_registro(solicitud, revisado_por, motivo=""):
    user = solicitud.usuario
    user.estado_solicitud = User.ESTADO_RECHAZADA
    user.is_active = True
    user.save(update_fields=["estado_solicitud", "is_active"])

    solicitud.estado = SolicitudRegistro.RECHAZADA
    solicitud.revisado_por = revisado_por
    solicitud.fecha_revision = timezone.now()
    solicitud.motivo_revision = (motivo or "").strip()
    solicitud.save(
        update_fields=["estado", "revisado_por", "fecha_revision", "motivo_revision"]
    )
    _notificar_estado_solicitud(solicitud, fue_aprobada=False)


def registro_view(request):
    if request.user.is_authenticated:
        return redirect("admin:index")

    if request.method == "POST":
        form = RegistroUsuarioForm(request.POST, request.FILES)
        if form.is_valid():
            opcion = form.cleaned_data["colegio_opcion"]
            institucion = form.cleaned_data.get("institucion")
            if opcion == RegistroUsuarioForm.OPCION_GENERAL:
                institucion = _get_or_create_institucion_general()

            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.estado_solicitud = User.ESTADO_PENDIENTE
            user.is_active = True
            user.is_staff = True
            user.save()

            SolicitudRegistro.objects.create(
                usuario=user,
                institucion_solicitada=institucion,
                telefono_whatsapp=form.cleaned_data["telefono_whatsapp"],
                mensaje=form.cleaned_data.get("mensaje", ""),
                comprobante_pago=form.cleaned_data.get("comprobante_pago"),
                estado=SolicitudRegistro.PENDIENTE,
            )
            messages.success(
                request,
                "Solicitud enviada. Tu cuenta quedó pendiente de aprobación.",
            )
            return redirect("admin:login")
    else:
        form = RegistroUsuarioForm()

    return render(request, "core/registro.html", {"form": form})

def seleccionar_institucion(request):
    """
    Pantalla para elegir colegio.  Maneja 3 casos:

    1) El usuario NO tiene membresías   → solo muestra aviso + botón «Salir».
    2) Tiene exactamente 1 y está activa → la selecciona automáticamente.
    3) Tiene varias                    → muestra el formulario de selección.
    """
    user = request.user
    # 0. Superusuario no pasa por aquí
    if user.is_superuser:
        return redirect("admin:index")

    membresias = user.membresias.select_related("institucion")
    membresias_activas = [m for m in membresias if m.institucion and m.institucion.activa]

    # 1) Sin membresías --------------► renderizar aviso
    if not membresias_activas:
        return render(
            request,
            "core/seleccionar_institucion.html",
            {"membresias": []}
        )

    # 2) Una sola membresía activa ----► autoselección
    if len(membresias_activas) == 1:
        inst = membresias_activas[0].institucion
        request.session["institucion_id"] = inst.id
        return redirect("admin:index")

    # 3) Varias membresías -------------► formulario
    if request.method == "POST":
        inst_id = request.POST.get("institucion_id")
        if inst_id:
            try:
                inst_id_int = int(inst_id)
            except (TypeError, ValueError):
                messages.error(request, _("La institución seleccionada no es válida."))
                return redirect("seleccionar_institucion")

            permitidas = {m.institucion_id for m in membresias_activas}
            if inst_id_int not in permitidas:
                messages.error(request, _("No tienes acceso a la institución seleccionada."))
                return redirect("seleccionar_institucion")

            request.session["institucion_id"] = inst_id_int
            return redirect("admin:index")
        # Si llegó aquí es porque pulsó «Entrar» sin elegir
        messages.error(request, _("Debe seleccionar una institución."))

    return render(
        request,
        "core/seleccionar_institucion.html",
        {"membresias": membresias_activas}
    )
