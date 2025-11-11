from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from core.models import Miembro
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

@receiver(user_logged_in)
def asignar_institucion_automaticamente(sender, user, request, **kwargs):
    """
    Signal que se ejecuta después de un login exitoso.
    Asigna automáticamente la institución si el usuario solo tiene una.
    """
    try:
        # Solo procesar si no es superusuario
        if user.is_superuser:
            logger.debug(f"Usuario {user.email} es superusuario - no se asigna institución")
            return
        
        logger.info(f"Signal user_logged_in ejecutándose para usuario: {user.email}")
        
        # Verificar si ya hay institución en sesión
        if request.session.get("institucion_id"):
            logger.debug(f"Usuario {user.email} ya tiene institución en sesión")
            return
        
        # Verificar membresías
        membresias = user.membresias.select_related("institucion").all()
        logger.debug(f"Usuario {user.email} tiene {membresias.count()} membresías")
        
        # Si tiene exactamente 1 institución válida, asignarla automáticamente
        if membresias.count() == 1:
            inst = membresias.first().institucion
            if inst.activa:
                logger.info(f"Asignando automáticamente institución única: {inst.nombre}")
                request.session["institucion_id"] = inst.pk
                request.session.save()
                
                # También establecer en el request para que esté disponible inmediatamente
                request.institucion_activa_id = inst.pk
            else:
                logger.warning(f"Institución única {inst.nombre} no está activa")
        elif membresias.count() > 1:
            logger.info(f"Usuario {user.email} tiene múltiples instituciones - debe seleccionar")
        else:
            logger.warning(f"Usuario {user.email} no tiene membresías")
            
    except Exception as e:
        logger.error(f"Error en signal asignar_institucion_automaticamente: {e}", exc_info=True)






























