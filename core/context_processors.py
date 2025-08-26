from core.models import Institucion

def institucion_activa(request):
    """
    Context processor que hace disponible la institución activa
    en todas las plantillas y vistas.
    """
    if hasattr(request, 'institucion_activa_id') and request.institucion_activa_id:
        try:
            institucion = Institucion.objects.get(pk=request.institucion_activa_id)
            return {
                'institucion_activa': institucion,
                'institucion_activa_id': request.institucion_activa_id
            }
        except Institucion.DoesNotExist:
            pass
    
    return {
        'institucion_activa': None,
        'institucion_activa_id': None
    }