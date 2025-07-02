from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import Provincia, Canton, Distrito
import logging

logger = logging.getLogger(__name__)

@require_GET
def api_cantones(request, provincia_id):
    try:
        provincia = Provincia.objects.get(id=provincia_id)
        cantones = list(provincia.cantones.all().order_by('nombre').values('id', 'nombre'))
        
        logger.info(f"Cantones para provincia {provincia_id} ({provincia.nombre}): {len(cantones)} encontrados")
        
        return JsonResponse(cantones, safe=False)
        
    except Provincia.DoesNotExist:
        return JsonResponse([], safe=False)
    except Exception as e:
        logger.error(f"Error en api_cantones: {str(e)}", exc_info=True)
        return JsonResponse([{'error': str(e)}], safe=False, status=500)

@require_GET
def api_distritos(request, canton_id):
    try:
        canton = Canton.objects.get(id=canton_id)
        distritos = list(canton.distritos.all().order_by('nombre').values('id', 'nombre'))
        
        logger.info(f"Distritos para cantón {canton_id} ({canton.nombre}): {len(distritos)} encontrados")
        
        return JsonResponse(distritos, safe=False)
        
    except Canton.DoesNotExist:
        return JsonResponse([], safe=False)
    except Exception as e:
        logger.error(f"Error en api_distritos: {str(e)}", exc_info=True)
        return JsonResponse([{'error': str(e)}], safe=False, status=500)