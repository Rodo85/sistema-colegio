from django.shortcuts import redirect
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
    Prioridad: 1 membresía → 1 Profesor → None (debe elegir).
    """
    membresias = list(user.membresias.select_related("institucion").all())
    if len(membresias) == 1:
        inst = membresias[0].institucion
        if inst.activa:
            return inst
    if len(membresias) > 1:
        # Docente con varias membresías: usar institución de su único Profesor
        from config_institucional.models import Profesor
        profesores = list(Profesor.objects.filter(usuario=user).select_related("institucion"))
        if len(profesores) == 1:
            inst = profesores[0].institucion
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
