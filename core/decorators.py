from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from functools import wraps
from core.models import Institucion
import logging

logger = logging.getLogger(__name__)

def require_institucion(view_func):
    """
    Decorator que asegura que el usuario tenga una institución activa.
    Si no la tiene y solo tiene una membresía, la asigna automáticamente.
    Si tiene múltiples, redirige a selección.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        
        # Superusuario no necesita institución
        if user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Verificar si ya hay institución activa
        if hasattr(request, 'institucion_activa_id') and request.institucion_activa_id:
            return view_func(request, *args, **kwargs)
        
        # Verificar si hay institución en sesión
        inst_id = request.session.get("institucion_id")
        if inst_id:
            try:
                inst = Institucion.objects.get(pk=inst_id)
                if inst.activa:
                    request.institucion_activa_id = inst_id
                    return view_func(request, *args, **kwargs)
                else:
                    # Institución inactiva, limpiar sesión
                    request.session.pop("institucion_id", None)
            except Institucion.DoesNotExist:
                request.session.pop("institucion_id", None)
        
        # No hay institución activa, verificar membresías
        try:
            membresias = user.membresias.select_related("institucion").all()
            
            # Si tiene exactamente 1 institución válida, asignarla automáticamente
            if membresias.count() == 1:
                inst = membresias.first().institucion
                if inst.activa:
                    logger.info(f"Decorator: Asignando automáticamente institución única: {inst.nombre}")
                    request.session["institucion_id"] = inst.pk
                    request.institucion_activa_id = inst.pk
                    request.session.save()
                    return view_func(request, *args, **kwargs)
                else:
                    logger.warning(f"Institución única {inst.nombre} no está activa")
            
            # Si tiene múltiples instituciones o ninguna válida, redirigir a selección
            if request.path != "/seleccionar-institucion/":
                logger.info("Decorator: Redirigiendo a selección de institución")
                return redirect("seleccionar_institucion")
            else:
                return view_func(request, *args, **kwargs)
                
        except Exception as e:
            logger.error(f"Error en decorator require_institucion: {e}", exc_info=True)
            # En caso de error, redirigir a selección de institución
            if request.path != "/seleccionar-institucion/":
                return redirect("seleccionar_institucion")
            else:
                return view_func(request, *args, **kwargs)
    
    return wrapper


def ensure_institucion_activa(view_func):
    """
    Decorator que asegura que la institución activa esté disponible en la vista.
    No redirige, solo asigna la institución si está disponible.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        
        # Superusuario no necesita institución
        if user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Si ya hay institución activa, no hacer nada
        if hasattr(request, 'institucion_activa_id') and request.institucion_activa_id:
            return view_func(request, *args, **kwargs)
        
        # Verificar si hay institución en sesión
        inst_id = request.session.get("institucion_id")
        if inst_id:
            try:
                inst = Institucion.objects.get(pk=inst_id)
                if inst.activa:
                    request.institucion_activa_id = inst_id
                    return view_func(request, *args, **kwargs)
                else:
                    # Institución inactiva, limpiar sesión
                    request.session.pop("institucion_id", None)
            except Institucion.DoesNotExist:
                request.session.pop("institucion_id", None)
        
        # No hay institución activa, verificar membresías
        try:
            membresias = user.membresias.select_related("institucion").all()
            
            # Si tiene exactamente 1 institución válida, asignarla automáticamente
            if membresias.count() == 1:
                inst = membresias.first().institucion
                if inst.activa:
                    logger.info(f"Decorator ensure_institucion_activa: Asignando automáticamente institución única: {inst.nombre}")
                    request.session["institucion_id"] = inst.pk
                    request.institucion_activa_id = inst.pk
                    request.session.save()
                    return view_func(request, *args, **kwargs)
            
            # Si no hay institución activa, continuar sin ella
            return view_func(request, *args, **kwargs)
                
        except Exception as e:
            logger.error(f"Error en decorator ensure_institucion_activa: {e}", exc_info=True)
            # En caso de error, continuar sin institución
            return view_func(request, *args, **kwargs)
    
    return wrapper
