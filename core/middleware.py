from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from core.models import Institucion
import logging

logger = logging.getLogger(__name__)

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
        
        # Si ya está en la pantalla de selección de institución, no hacer nada
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
            
            # No hay institución activa, verificar membresías
            membresias = user.membresias.select_related("institucion").all()
            logger.debug(f"Usuario {user.email} tiene {membresias.count()} membresías")
            
            # Si tiene exactamente 1 institución válida, asignarla automáticamente
            if membresias.count() == 1:
                inst = membresias.first().institucion
                if inst.activa:
                    logger.info(f"Asignando automáticamente institución única: {inst.nombre}")
                    request.session["institucion_id"] = inst.pk
                    request.institucion_activa_id = inst.pk
                    request.session.save()
                    return None
                else:
                    logger.warning(f"Institución única {inst.nombre} no está activa")
            
            # Si tiene múltiples instituciones o ninguna válida, redirigir a selección
            logger.info("Redirigiendo a selección de institución")
            return redirect("seleccionar_institucion")
            
        except Exception as e:
            logger.error(f"Error en process_view: {e}", exc_info=True)
            # En caso de error, redirigir a selección de institución
            return redirect("seleccionar_institucion")
    
    def process_request(self, request):
        """
        Este método se ejecuta antes de que se resuelva la vista.
        Solo establecemos la institución activa si ya está en sesión.
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
        
        return None
