from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin
from core.models import Institucion
import logging

logger = logging.getLogger(__name__)

ALLOWED_PATH_PREFIXES = (
    "/seleccionar-institucion/",
    "/admin/logout",   # permitir salir aunque no haya institución
)


def _asignar_institucion_sesion(request, inst_id):
    """Asigna institución a sesión y request."""
    request.session["institucion_id"] = inst_id
    request.institucion_activa_id = inst_id
    request.session.save()


def _obtener_institucion_default(user):
    """
    Obtiene la institución por defecto para el usuario.
    Regla: solo autoseleccionar cuando existe exactamente 1 membresía activa.
    Si tiene varias membresías, debe elegir explícitamente.
    """
    membresias = list(user.membresias.select_related("institucion").all())
    if len(membresias) == 1:
        inst = membresias[0].institucion
        if inst.activa:
            return inst
    return None


class InstitucionMiddleware(MiddlewareMixin):

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Este método se ejecuta después de que se resuelve la vista pero antes de que se ejecute.
        Es el lugar perfecto para asegurar que la institución esté asignada.
        """
        user = getattr(request, "user", None)
        
        # Solo procesar si el usuario está autenticado
        if not user or not user.is_authenticated:
            return None
        
        # Superusuario no necesita institución
        if user.is_superuser:
            return None
        
        # Si ya hay institución activa, no hacer nada
        if hasattr(request, 'institucion_activa_id') and request.institucion_activa_id:
            return None
        
        # Permitir rutas que no deben exigir institución (logout, selector, etc.)
        for prefijo in ALLOWED_PATH_PREFIXES:
            if request.path.startswith(prefijo):
                return None
        # Si ya está en la pantalla de selección de institución, no hacer nada (cubierto por prefijos)
        if request.path == "/seleccionar-institucion/":
            return None
        
        try:
            logger.debug(f"process_view: Procesando usuario {user.email}")
            
            # Verificar si ya hay institución en sesión
            inst_id = request.session.get("institucion_id")
            if inst_id:
                try:
                    inst = Institucion.objects.get(pk=inst_id)
                    if inst.activa:
                        request.institucion_activa_id = inst_id
                        logger.debug(f"Institución ya seleccionada: {inst.nombre}")
                        return None
                    else:
                        # Institución inactiva, limpiar sesión
                        logger.warning(f"Institución {inst_id} no está activa, limpiando sesión")
                        request.session.pop("institucion_id", None)
                except Institucion.DoesNotExist:
                    request.session.pop("institucion_id", None)
            
            # No hay institución en sesión: intentar asignar por defecto
            inst_default = _obtener_institucion_default(user)
            if inst_default:
                logger.info(f"Asignando institución por defecto: {inst_default.nombre}")
                _asignar_institucion_sesion(request, inst_default.pk)
                return None
            
            # Sin membresías o varias sin default: redirigir a selección
            logger.info("Redirigiendo a selección de institución")
            return redirect("seleccionar_institucion")
            
        except Exception as e:
            logger.error(f"Error en process_view: {e}", exc_info=True)
            # En caso de error, redirigir a selección de institución
            return redirect("seleccionar_institucion")
    
    def process_request(self, request):
        """
        Este método se ejecuta antes de que se resuelva la vista.
        Establece la institución activa desde sesión o asigna por defecto si aplica.
        """
        user = getattr(request, "user", None)
        
        # Solo procesar si el usuario está autenticado
        if not user or not user.is_authenticated:
            return None
        
        # Superusuario no necesita institución
        if user.is_superuser:
            return None
        
        # Si ya hay institución activa, no hacer nada
        if hasattr(request, 'institucion_activa_id') and request.institucion_activa_id:
            return None
        
        # Permitir rutas de salida/selector antes de imponer institución
        for prefijo in ALLOWED_PATH_PREFIXES:
            if request.path.startswith(prefijo):
                return None

        # Verificar si ya hay institución en sesión
        inst_id = request.session.get("institucion_id")
        if inst_id:
            try:
                inst = Institucion.objects.get(pk=inst_id)
                if inst.activa:
                    request.institucion_activa_id = inst_id
                    logger.debug(f"process_request: Institución ya seleccionada: {inst.nombre}")
                else:
                    # Institución inactiva, limpiar sesión
                    logger.warning(f"process_request: Institución {inst_id} no está activa, limpiando sesión")
                    request.session.pop("institucion_id", None)
            except Institucion.DoesNotExist:
                request.session.pop("institucion_id", None)
        else:
            # Sin sesión: asignar por defecto si tiene 1 membresía o 1 Profesor
            inst_default = _obtener_institucion_default(user)
            if inst_default:
                request.session["institucion_id"] = inst_default.pk
                request.institucion_activa_id = inst_default.pk
                logger.debug(f"process_request: Institución por defecto asignada: {inst_default.nombre}")
        
        return None


class SessionTimeoutMiddleware(MiddlewareMixin):
    """
    Ajusta el tiempo de expiración de sesión por preferencia del usuario.
    """

    def process_request(self, request):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        try:
            timeout = user.timeout_sesion_segundos()
            request.session.set_expiry(timeout)
        except Exception:
            # Nunca bloquear navegación por un error de preferencia.
            return None
        return None


class PagoControlMiddleware(MiddlewareMixin):
    """
    Controla alertas de pago y bloquea acceso cuando la fecha límite vence.
    """

    RUTAS_PERMITIDAS = (
        "/admin/login/",
        "/admin/logout/",
        "/password-reset/",
        "/registro/",
    )

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or user.is_superuser:
            return None

        path = request.path or ""
        if any(path.startswith(p) for p in self.RUTAS_PERMITIDAS):
            return None

        fecha_limite = getattr(user, "fecha_limite_pago", None)
        if fecha_limite and user.pago_vencido():
            logout(request)
            messages.error(
                request,
                "Tu período de prueba o acceso expiró. Contacta al administrador para renovar tu pago.",
            )
            return redirect("admin:login")

        dias = user.dias_para_vencer_pago()
        if (
            getattr(user, "estado_pago", None) == user.PAGO_PENDIENTE
            and dias is not None
            and 0 <= dias <= 3
        ):
            if dias == 0:
                texto = "Tu período de prueba vence hoy."
            elif dias == 1:
                texto = "Tu período de prueba vence mañana."
            else:
                texto = f"Tu período de prueba vence en {dias} días."
            messages.warning(request, f"{texto} Realiza el pago para evitar bloqueo.")

        return None
