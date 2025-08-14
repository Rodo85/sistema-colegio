from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.mail import send_mail
from core.models import Institucion
from ingreso_clases.utils import WhatsAppConfig, send_whatsapp_message

from matricula.models import Estudiante, EncargadoEstudiante
from .models import RegistroIngreso


def _obtener_encargado_principal(estudiante):
    return (
        EncargadoEstudiante.objects
        .filter(estudiante=estudiante, principal=True)
        .select_related("persona_contacto")
        .first()
    )


@csrf_exempt
def marcar_ingreso(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

    identificacion = (request.POST.get("identificacion") or "").strip()
    if not identificacion:
        return JsonResponse({"ok": False, "error": "Identificación requerida"}, status=400)

    try:
        estudiante = Estudiante.objects.get(identificacion=identificacion)
    except Estudiante.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Estudiante no encontrado"}, status=404)

    # Determinar si el último registro fue entrada o salida
    ultimo = RegistroIngreso.objects.filter(identificacion=identificacion).order_by("-fecha_hora").first()
    es_entrada = True if not ultimo else not ultimo.es_entrada

    registro = RegistroIngreso.objects.create(
        identificacion=identificacion,
        fecha_hora=timezone.now(),
        es_entrada=es_entrada,
    )

    # Notificar al encargado principal (correo y/o WhatsApp)
    encargado_p = _obtener_encargado_principal(estudiante)
    if encargado_p and encargado_p.persona_contacto.correo:
        accion = "ingresó a la institución" if es_entrada else "salió de la institución"
        mensaje = (
            f"El estudiante {estudiante.primer_apellido} {estudiante.nombres} {accion} "
            f"a las {registro.fecha_hora:%H:%M} del {registro.fecha_hora:%d/%m/%Y}."
        )
        try:
            send_mail(
                subject="Aviso de ingreso/salida",
                message=mensaje,
                from_email=None,
                recipient_list=[encargado_p.persona_contacto.correo],
                fail_silently=True,
            )
        except Exception:
            pass

        # WhatsApp si está configurado en la institución
        institucion = estudiante.institucion
        cfg = WhatsAppConfig(
            phone_from=getattr(institucion, 'whatsapp_phone', None),
            token=getattr(institucion, 'whatsapp_token', None),
            from_id=getattr(institucion, 'whatsapp_from_id', None),
        )
        tel_destino = getattr(encargado_p.persona_contacto, 'celular_avisos', '')
        if tel_destino:
            # Normalizar a E.164 si fuera necesario (se asume ya con prefijo país)
            try:
                send_whatsapp_message(cfg, tel_destino, mensaje)
            except Exception:
                pass

    return JsonResponse({"ok": True, "entrada": es_entrada, "fecha_hora": registro.fecha_hora})

