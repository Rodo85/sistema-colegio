from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction

from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db.models import Q

from .models import SeccionCursoLectivo, EspecialidadCursoLectivo, SubgrupoCursoLectivo
from catalogos.models import CursoLectivo, Seccion, Especialidad, Subgrupo
from core.models import Institucion
from core.decorators import ensure_institucion_activa


def obtener_curso_lectivo_activo():
    """
    Obtiene el curso lectivo activo basado en las fechas actuales.
    Si no hay ninguno activo por fechas, retorna el más reciente activo.
    """
    # Buscar curso lectivo activo basado en fechas
    curso_lectivo = CursoLectivo.objects.filter(
        Q(fecha_inicio__lte=timezone.now().date()) &
        Q(fecha_fin__gte=timezone.now().date()) &
        Q(activo=True)
    ).order_by('-anio').first()
    
    # Si no hay curso activo por fechas, usar el más reciente
    if not curso_lectivo:
        curso_lectivo = CursoLectivo.objects.filter(activo=True).order_by('-anio').first()
    
    return curso_lectivo

@staff_member_required
@ensure_institucion_activa
def gestionar_secciones_curso_lectivo(request):
    """
    Vista para gestionar secciones por curso lectivo de forma masiva.
    Permite seleccionar múltiples secciones y activarlas/desactivarlas de una vez.
    """
    # Obtener la institución activa del usuario
    if request.user.is_superuser:
        # Superusuario puede seleccionar cualquier institución
        institucion_id = request.GET.get('institucion')
        if institucion_id:
            institucion = get_object_or_404(Institucion, id=institucion_id)
        else:
            # Mostrar primera institución por defecto
            institucion = Institucion.objects.first()
    else:
        # Usuario normal solo puede ver su institución
        if hasattr(request, 'institucion_activa_id') and request.institucion_activa_id:
            try:
                institucion = Institucion.objects.get(pk=request.institucion_activa_id)
            except Institucion.DoesNotExist:
                institucion = None
        else:
            institucion = None
    
    # Obtener curso lectivo seleccionado
    curso_lectivo_id = request.GET.get('curso_lectivo')
    if curso_lectivo_id:
        curso_lectivo = get_object_or_404(CursoLectivo, id=curso_lectivo_id)
    else:
        # Mostrar curso lectivo activo (dentro del rango de fechas) por defecto
        from django.utils import timezone
        from django.db.models import Q
        
        # Buscar curso lectivo activo basado en fechas
        curso_lectivo = CursoLectivo.objects.filter(
            Q(fecha_inicio__lte=timezone.now().date()) &
            Q(fecha_fin__gte=timezone.now().date()) &
            Q(activo=True)
        ).order_by('-anio').first()
        
        # Si no hay curso activo por fechas, usar el más reciente
        if not curso_lectivo:
            curso_lectivo = CursoLectivo.objects.filter(activo=True).order_by('-anio').first()
    
    # Obtener todas las secciones disponibles
    secciones_disponibles = Seccion.objects.all().order_by('nivel__numero', 'numero')
    
    # Obtener secciones ya configuradas para este curso lectivo e institución
    secciones_configuradas = {}
    if institucion and curso_lectivo:
        secciones_existentes = SeccionCursoLectivo.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_lectivo
        ).select_related('seccion')
        
        for seccion_config in secciones_existentes:
            secciones_configuradas[seccion_config.seccion.id] = {
                'activa': seccion_config.activa,
                'id': seccion_config.id
            }
    
    # Obtener instituciones para el selector (solo para superusuarios)
    instituciones = Institucion.objects.all().order_by('nombre') if request.user.is_superuser else []
    
    # Obtener cursos lectivos disponibles
    cursos_lectivos = CursoLectivo.objects.all().order_by('-anio')
    
    context = {
        'institucion': institucion,
        'curso_lectivo': curso_lectivo,
        'secciones_configuradas': secciones_configuradas,
        'secciones_disponibles': secciones_disponibles,
        'instituciones': instituciones,
        'cursos_lectivos': cursos_lectivos,
        'es_superusuario': request.user.is_superuser,
    }
    
    return render(request, 'config_institucional/gestionar_secciones_curso_lectivo.html', context)

@staff_member_required
@require_http_methods(["POST"])
def actualizar_secciones_curso_lectivo(request):
    """
    Vista AJAX para actualizar secciones por curso lectivo.
    Permite crear, actualizar y eliminar registros de forma masiva.
    """
    try:
        institucion_id = request.POST.get('institucion_id')
        curso_lectivo_id = request.POST.get('curso_lectivo_id')
        secciones_data = request.POST.getlist('secciones[]')
        
        if not institucion_id or not curso_lectivo_id:
            return JsonResponse({'success': False, 'message': 'Faltan parámetros requeridos'})
        
        institucion = get_object_or_404(Institucion, id=institucion_id)
        curso_lectivo = get_object_or_404(CursoLectivo, id=curso_lectivo_id)
        
        with transaction.atomic():
            # Obtener secciones existentes
            secciones_existentes = SeccionCursoLectivo.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo
            )
            
            # Crear un diccionario para acceso rápido
            secciones_por_id = {sc.seccion_id: sc for sc in secciones_existentes}
            
            # Procesar cada sección
            creadas = 0
            actualizadas = 0
            eliminadas = 0
            
            # Obtener IDs de secciones procesadas
            secciones_procesadas = set()
            
            for seccion_data in secciones_data:
                if not seccion_data:
                    continue
                    
                try:
                    seccion_id, activa = seccion_data.split(':')
                    seccion_id = int(seccion_id)
                    activa = activa.lower() == 'true'
                    secciones_procesadas.add(seccion_id)
                    
                    if seccion_id in secciones_por_id:
                        # Actualizar existente
                        seccion_config = secciones_por_id[seccion_id]
                        if seccion_config.activa != activa:
                            seccion_config.activa = activa
                            seccion_config.save()
                            actualizadas += 1
                    else:
                        # Crear nuevo
                        seccion = get_object_or_404(Seccion, id=seccion_id)
                        SeccionCursoLectivo.objects.create(
                            institucion=institucion,
                            curso_lectivo=curso_lectivo,
                            seccion=seccion,
                            activa=activa
                        )
                        creadas += 1
                        
                except (ValueError, Seccion.DoesNotExist):
                    continue
            
            # Eliminar secciones que ya no están seleccionadas
            for seccion_config in secciones_existentes:
                if seccion_config.seccion_id not in secciones_procesadas:
                    seccion_config.delete()
                    eliminadas += 1
            
            return JsonResponse({
                'success': True,
                'message': f'Operación completada: {creadas} creadas, {actualizadas} actualizadas, {eliminadas} eliminadas'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

@staff_member_required
@ensure_institucion_activa
def gestionar_especialidades_curso_lectivo(request):
    """
    Vista para gestionar especialidades por curso lectivo de forma masiva.
    Similar a la gestión de secciones pero para especialidades.
    """
    # Obtener la institución activa del usuario
    if request.user.is_superuser:
        institucion_id = request.GET.get('institucion')
        if institucion_id:
            institucion = get_object_or_404(Institucion, id=institucion_id)
        else:
            institucion = Institucion.objects.first()
    else:
        if hasattr(request, 'institucion_activa_id') and request.institucion_activa_id:
            try:
                institucion = Institucion.objects.get(pk=request.institucion_activa_id)
            except Institucion.DoesNotExist:
                institucion = None
        else:
            institucion = None
    
    # Obtener curso lectivo seleccionado
    curso_lectivo_id = request.GET.get('curso_lectivo')
    if curso_lectivo_id:
        curso_lectivo = get_object_or_404(CursoLectivo, id=curso_lectivo_id)
    else:
        # Mostrar curso lectivo activo (dentro del rango de fechas) por defecto
        from django.utils import timezone
        from django.db.models import Q
        
        # Buscar curso lectivo activo basado en fechas
        curso_lectivo = CursoLectivo.objects.filter(
            Q(fecha_inicio__lte=timezone.now().date()) &
            Q(fecha_fin__gte=timezone.now().date()) &
            Q(activo=True)
        ).order_by('-anio').first()
        
        # Si no hay curso activo por fechas, usar el más reciente
        if not curso_lectivo:
            curso_lectivo = CursoLectivo.objects.filter(activo=True).order_by('-anio').first()
    
    # Obtener todas las especialidades disponibles
    especialidades_disponibles = Especialidad.objects.all().order_by('modalidad__nombre', 'nombre')
    
    # Obtener especialidades ya configuradas
    especialidades_configuradas = {}
    if institucion and curso_lectivo:
        especialidades_existentes = EspecialidadCursoLectivo.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_lectivo
        ).select_related('especialidad')
        
        for especialidad_config in especialidades_existentes:
            especialidades_configuradas[especialidad_config.especialidad.id] = {
                'activa': especialidad_config.activa,
                'id': especialidad_config.id
            }
    
    # Obtener instituciones para el selector (solo para superusuarios)
    instituciones = Institucion.objects.all().order_by('nombre') if request.user.is_superuser else []
    
    # Obtener cursos lectivos disponibles
    cursos_lectivos = CursoLectivo.objects.all().order_by('-anio')
    
    context = {
        'institucion': institucion,
        'curso_lectivo': curso_lectivo,
        'especialidades_configuradas': especialidades_configuradas,
        'especialidades_disponibles': especialidades_disponibles,
        'instituciones': instituciones,
        'cursos_lectivos': cursos_lectivos,
        'es_superusuario': request.user.is_superuser,
    }
    
    return render(request, 'config_institucional/gestionar_especialidades_curso_lectivo.html', context)

@staff_member_required
@require_http_methods(["POST"])
def actualizar_especialidades_curso_lectivo(request):
    """
    Vista AJAX para actualizar especialidades por curso lectivo.
    """
    try:
        institucion_id = request.POST.get('institucion_id')
        curso_lectivo_id = request.POST.get('curso_lectivo_id')
        especialidades_data = request.POST.getlist('especialidades[]')
        
        if not institucion_id or not curso_lectivo_id:
            return JsonResponse({'success': False, 'message': 'Faltan parámetros requeridos'})
        
        institucion = get_object_or_404(Institucion, id=institucion_id)
        curso_lectivo = get_object_or_404(CursoLectivo, id=curso_lectivo_id)
        
        with transaction.atomic():
            # Obtener especialidades existentes
            especialidades_existentes = EspecialidadCursoLectivo.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo
            )
            
            # Crear un diccionario para acceso rápido
            especialidades_por_id = {ec.especialidad_id: ec for ec in especialidades_existentes}
            
            # Procesar cada especialidad
            creadas = 0
            actualizadas = 0
            eliminadas = 0
            
            # Obtener IDs de especialidades procesadas
            especialidades_procesadas = set()
            
            for especialidad_data in especialidades_data:
                if not especialidad_data:
                    continue
                    
                try:
                    especialidad_id, activa = especialidad_data.split(':')
                    especialidad_id = int(especialidad_id)
                    activa = activa.lower() == 'true'
                    especialidades_procesadas.add(especialidad_id)
                    
                    if especialidad_id in especialidades_por_id:
                        # Actualizar existente
                        especialidad_config = especialidades_por_id[especialidad_id]
                        if especialidad_config.activa != activa:
                            especialidad_config.activa = activa
                            especialidad_config.save()
                            actualizadas += 1
                    else:
                        # Crear nuevo
                        especialidad = get_object_or_404(Especialidad, id=especialidad_id)
                        EspecialidadCursoLectivo.objects.create(
                            institucion=institucion,
                            curso_lectivo=curso_lectivo,
                            especialidad=especialidad,
                            activa=activa
                        )
                        creadas += 1
                        
                except (ValueError, Especialidad.DoesNotExist):
                    continue
            
            # Eliminar especialidades que ya no están seleccionadas
            for especialidad_config in especialidades_existentes:
                if especialidad_config.especialidad_id not in especialidades_procesadas:
                    especialidad_config.delete()
                    eliminadas += 1
            
            return JsonResponse({
                'success': True,
                'message': f'Operación completada: {creadas} creadas, {actualizadas} actualizadas, {eliminadas} eliminadas'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

@staff_member_required
@ensure_institucion_activa
def gestionar_subgrupos_curso_lectivo(request):
    """
    Vista para gestionar subgrupos por curso lectivo de forma masiva.
    Permite seleccionar múltiples subgrupos y activarlos/desactivarlos de una vez.
    """
    # Obtener la institución activa del usuario
    if request.user.is_superuser:
        # Superusuario puede seleccionar cualquier institución
        institucion_id = request.GET.get('institucion')
        if institucion_id:
            institucion = get_object_or_404(Institucion, id=institucion_id)
        else:
            # Mostrar primera institución por defecto
            institucion = Institucion.objects.first()
    else:
        # Usuario normal solo puede ver su institución
        if hasattr(request, 'institucion_activa_id') and request.institucion_activa_id:
            try:
                institucion = Institucion.objects.get(pk=request.institucion_activa_id)
            except Institucion.DoesNotExist:
                institucion = None
        else:
            institucion = None
    
    # Obtener curso lectivo seleccionado
    curso_lectivo_id = request.GET.get('curso_lectivo')
    if curso_lectivo_id:
        curso_lectivo = get_object_or_404(CursoLectivo, id=curso_lectivo_id)
    else:
        # Mostrar curso lectivo activo (dentro del rango de fechas) por defecto
        from django.utils import timezone
        from django.db.models import Q
        
        # Buscar curso lectivo activo basado en fechas
        curso_lectivo = CursoLectivo.objects.filter(
            Q(fecha_inicio__lte=timezone.now().date()) &
            Q(fecha_fin__gte=timezone.now().date()) &
            Q(activo=True)
        ).order_by('-anio').first()
        
        # Si no hay curso activo por fechas, usar el más reciente
        if not curso_lectivo:
            curso_lectivo = CursoLectivo.objects.filter(activo=True).order_by('-anio').first()
    
    # Obtener todos los subgrupos disponibles
    subgrupos_disponibles = Subgrupo.objects.all().order_by('seccion__nivel__numero', 'seccion__numero', 'letra')
    
    # Obtener subgrupos ya configurados para este curso lectivo e institución
    subgrupos_configurados = {}
    if institucion and curso_lectivo:
        subgrupos_existentes = SubgrupoCursoLectivo.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_lectivo
        ).select_related('subgrupo', 'subgrupo__seccion', 'subgrupo__seccion__nivel')
        
        for subgrupo_config in subgrupos_existentes:
            subgrupos_configurados[subgrupo_config.subgrupo.id] = {
                'activa': subgrupo_config.activa,
                'id': subgrupo_config.id
            }
    
    # Obtener instituciones para el selector (solo para superusuarios)
    instituciones = Institucion.objects.all().order_by('nombre') if request.user.is_superuser else []
    
    # Obtener cursos lectivos disponibles
    cursos_lectivos = CursoLectivo.objects.all().order_by('-anio')
    
    context = {
        'institucion': institucion,
        'curso_lectivo': curso_lectivo,
        'subgrupos_configurados': subgrupos_configurados,
        'subgrupos_disponibles': subgrupos_disponibles,
        'instituciones': instituciones,
        'cursos_lectivos': cursos_lectivos,
        'es_superusuario': request.user.is_superuser,
    }
    
    return render(request, 'config_institucional/gestionar_subgrupos_curso_lectivo.html', context)

@staff_member_required
@require_http_methods(["POST"])
def actualizar_subgrupos_curso_lectivo(request):
    """
    Vista AJAX para actualizar subgrupos por curso lectivo.
    Permite crear, actualizar y eliminar registros de forma masiva.
    """
    try:
        institucion_id = request.POST.get('institucion_id')
        curso_lectivo_id = request.POST.get('curso_lectivo_id')
        subgrupos_data = request.POST.getlist('subgrupos[]')
        
        if not institucion_id or not curso_lectivo_id:
            return JsonResponse({'success': False, 'message': 'Faltan parámetros requeridos'})
        
        institucion = get_object_or_404(Institucion, id=institucion_id)
        curso_lectivo = get_object_or_404(CursoLectivo, id=curso_lectivo_id)
        
        with transaction.atomic():
            # Obtener subgrupos existentes
            subgrupos_existentes = SubgrupoCursoLectivo.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo
            )
            
            # Crear un diccionario para acceso rápido
            subgrupos_por_id = {sg.subgrupo_id: sg for sg in subgrupos_existentes}
            
            # Procesar cada subgrupo
            creados = 0
            actualizados = 0
            eliminados = 0
            
            # Obtener IDs de subgrupos procesados
            subgrupos_procesados = set()
            
            for subgrupo_data in subgrupos_data:
                if not subgrupo_data:
                    continue
                    
                try:
                    subgrupo_id, activa = subgrupo_data.split(':')
                    subgrupo_id = int(subgrupo_id)
                    activa = activa.lower() == 'true'
                    subgrupos_procesados.add(subgrupo_id)
                    
                    if subgrupo_id in subgrupos_por_id:
                        # Actualizar existente
                        subgrupo_config = subgrupos_por_id[subgrupo_id]
                        if subgrupo_config.activa != activa:
                            subgrupo_config.activa = activa
                            subgrupo_config.save()
                            actualizados += 1
                    else:
                        # Crear nuevo
                        subgrupo = get_object_or_404(Subgrupo, id=subgrupo_id)
                        SubgrupoCursoLectivo.objects.create(
                            institucion=institucion,
                            curso_lectivo=curso_lectivo,
                            subgrupo=subgrupo,
                            activa=activa
                        )
                        creados += 1
                        
                except (ValueError, Subgrupo.DoesNotExist):
                    continue
            
            # Eliminar subgrupos que ya no están seleccionados
            for subgrupo_config in subgrupos_existentes:
                if subgrupo_config.subgrupo_id not in subgrupos_procesados:
                    subgrupo_config.delete()
                    eliminados += 1
            
            return JsonResponse({
                'success': True,
                'message': f'Operación completada: {creados} creados, {actualizados} actualizados, {eliminados} eliminados'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})


# ════════════════════════════════════════════════════════════════
#                    DJANGO AUTOCOMPLETE LIGHT (DAL)
# ════════════════════════════════════════════════════════════════

from dal import autocomplete

class EspecialidadCursoLectivoAutocomplete(autocomplete.Select2QuerySetView):
    """
    Autocomplete para EspecialidadCursoLectivo que filtra por institución y curso lectivo.
    Se usa en el admin de SubgrupoCursoLectivo para el campo especialidad_curso.
    """
    
    def get_queryset(self):
        print("🔥 EspecialidadCursoLectivoAutocomplete.get_queryset() llamado")
        
        if not self.request.user.is_authenticated:
            print("❌ Usuario no autenticado")
            return EspecialidadCursoLectivo.objects.none()
        
        print(f"👤 Usuario: {self.request.user.email} (superuser: {self.request.user.is_superuser})")
        
        # Obtener institución del usuario
        institucion_id = getattr(self.request, 'institucion_activa_id', None)
        print(f"🏢 Institución activa ID: {institucion_id}")
        
        if not institucion_id:
            # Para superusuario, usar institución del forward si está disponible
            if self.request.user.is_superuser:
                institucion_forward = self.forwarded.get('institucion_id', None)
                if institucion_forward:
                    institucion_id = institucion_forward
                    print(f"👑 Superusuario - usando institución del forward: {institucion_id}")
                else:
                    print("❌ Superusuario sin institución en forward")
                    return EspecialidadCursoLectivo.objects.none()
            else:
                print("❌ No hay institución activa")
                return EspecialidadCursoLectivo.objects.none()
        
        # FILTRO POR CURSO LECTIVO (forward)
        curso_lectivo_id = self.forwarded.get('curso_lectivo_id', None)
        print(f"📅 Curso lectivo ID del forward: {curso_lectivo_id}")
        print(f"📅 Forwarded completo: {self.forwarded}")
        
        # Inicializar queryset
        qs = EspecialidadCursoLectivo.objects.none()
        
        # REQUIERE tanto institución como curso lectivo
        if curso_lectivo_id and institucion_id:
            try:
                # Obtener especialidades configuradas y activas para esta institución y curso lectivo
                qs = EspecialidadCursoLectivo.objects.filter(
                    institucion_id=institucion_id,
                    curso_lectivo_id=curso_lectivo_id,
                    activa=True
                ).select_related('especialidad', 'especialidad__modalidad')
                
                print(f"🎯 Especialidades configuradas encontradas: {[ecl.especialidad.nombre for ecl in qs]}")
                
            except (ValueError, Exception) as e:
                print(f"❌ Error: {e}")
                return EspecialidadCursoLectivo.objects.none()
        else:
            # Sin curso lectivo o institución, no mostrar especialidades
            if not curso_lectivo_id:
                print("❌ No hay curso lectivo seleccionado")
            if not institucion_id:
                print("❌ No hay institución")
            return EspecialidadCursoLectivo.objects.none()
        
        # Filtro por búsqueda
        if self.q:
            qs = qs.filter(especialidad__nombre__icontains=self.q)
            print(f"🔍 Filtrado por búsqueda '{self.q}': {[ecl.especialidad.nombre for ecl in qs]}")
        
        final_qs = qs.order_by('especialidad__nombre')
        print(f"🎯 RESULTADO FINAL: {[ecl.especialidad.nombre for ecl in final_qs]}")
        return final_qs
    
    def get_result_label(self, result):
        """Personalizar la etiqueta mostrada en el resultado"""
        return f"{result.especialidad.nombre}"
    
    def get_result_value(self, result):
        """Valor que se almacena cuando se selecciona el resultado"""
        return str(result.id)