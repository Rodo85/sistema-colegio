from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from config_institucional.models import Nivel
from catalogos.models import CursoLectivo, Seccion, Subgrupo, Especialidad
from core.models import Institucion
from .models import Estudiante, MatriculaAcademica
from dal import autocomplete
import json

@login_required
def consulta_estudiante(request):
    estudiante = None
    matricula = None
    encargados = []
    curso_lectivo = None
    identificacion = ''
    error = ''
    institucion = None
    edad_estudiante = ""
    
    # Obtener todos los cursos lectivos disponibles para el select
    cursos_lectivos = CursoLectivo.objects.all().order_by('-anio')
    
    # Obtener instituciones disponibles solo para superusuario
    instituciones = []
    if request.user.is_superuser:
        instituciones = Institucion.objects.all().order_by('nombre')
    
    if request.method == 'POST':
        curso_lectivo_id = request.POST.get('curso_lectivo')
        identificacion = request.POST.get('identificacion', '').strip()
        institucion_id = request.POST.get('institucion')
        
        if not curso_lectivo_id or not identificacion:
            error = 'Debe seleccionar un curso lectivo e ingresar la identificación del estudiante.'
        elif request.user.is_superuser and not institucion_id:
            error = 'Debe seleccionar una institución.'
        else:
            try:
                curso_lectivo = CursoLectivo.objects.get(pk=curso_lectivo_id)
                
                # Determinar la institución según el tipo de usuario
                if request.user.is_superuser:
                    institucion = Institucion.objects.get(pk=institucion_id)
                else:
                    # Usuario normal: usar institución activa
                    institucion_id = getattr(request, 'institucion_activa_id', None)
                    if not institucion_id:
                        error = 'No se pudo determinar la institución activa.'
                        return render(request, 'matricula/consulta_estudiante.html', {
                            'error': error,
                            'cursos_lectivos': cursos_lectivos,
                            'instituciones': instituciones,
                            'es_superusuario': request.user.is_superuser,
                        })
                    institucion = Institucion.objects.get(pk=institucion_id)
                
                # Buscar estudiante por identificación e institución
                estudiante = Estudiante.objects.get(
                    identificacion=identificacion,
                    institucion=institucion
                )
                
                # Buscar matrícula activa para el curso seleccionado
                matricula = MatriculaAcademica.objects.filter(
                    estudiante=estudiante,
                    curso_lectivo=curso_lectivo,
                    estado__iexact='activo'
                ).first()
                
                if matricula:
                    # Si hay matrícula activa, obtener encargados
                    encargados = estudiante.encargadoestudiante_set.select_related(
                        'persona_contacto', 'parentesco'
                    ).all()
                    
                    # Calcular edad del estudiante
                    if estudiante.fecha_nacimiento:
                        from datetime import date
                        today = date.today()
                        edad_estudiante = today.year - estudiante.fecha_nacimiento.year - (
                            (today.month, today.day) < (
                                estudiante.fecha_nacimiento.month, 
                                estudiante.fecha_nacimiento.day
                            )
                        )
                        edad_estudiante = f"{edad_estudiante} años"
                else:
                    # No hay matrícula activa, mostrar error
                    estudiante = None
                    institucion = None
                    encargados = []
                    error = f'No existe matrícula activa para el estudiante con identificación {identificacion} en el curso lectivo {curso_lectivo.nombre}.'
                    
            except CursoLectivo.DoesNotExist:
                error = 'El curso lectivo seleccionado no existe.'
            except Institucion.DoesNotExist:
                error = 'La institución seleccionada no existe.'
            except Estudiante.DoesNotExist:
                error = f'No se encontró ningún estudiante con la identificación {identificacion} en la institución {institucion.nombre}.'
            except Exception as e:
                error = f'Error inesperado: {str(e)}'
    
    context = {
        'estudiante': estudiante,
        'matricula': matricula,
        'encargados': encargados,
        'curso_lectivo': curso_lectivo,
        'identificacion': identificacion,
        'error': error,
        'institucion': institucion,
        'edad_estudiante': edad_estudiante,
        'cursos_lectivos': cursos_lectivos,
        'instituciones': instituciones,
        'es_superusuario': request.user.is_superuser,
    }
    
    return render(request, 'matricula/consulta_estudiante.html', context)

@csrf_exempt
@login_required
def get_especialidades_disponibles(request):
    """
    Vista AJAX para obtener las especialidades disponibles según el curso lectivo
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        curso_lectivo_id = request.POST.get('curso_lectivo_id')
        if not curso_lectivo_id:
            return JsonResponse({'success': False, 'error': 'ID de curso lectivo requerido'})
        
        # Obtener la institución del usuario
        institucion_id = getattr(request, 'institucion_activa_id', None)
        if not institucion_id:
            return JsonResponse({'success': False, 'error': 'No se pudo determinar la institución'})
        
        # Obtener el curso lectivo y la institución
        from core.models import Institucion
        curso_lectivo = CursoLectivo.objects.get(id=curso_lectivo_id, institucion_id=institucion_id)
        institucion = Institucion.objects.get(id=institucion_id)
        
        # Obtener especialidades disponibles
        especialidades_disponibles = MatriculaAcademica.get_especialidades_disponibles(
            institucion=institucion,
            curso_lectivo=curso_lectivo
        )
        
        # Preparar datos para JSON
        especialidades_data = []
        for esp in especialidades_disponibles:
            especialidades_data.append({
                'id': esp.id,
                'nombre': esp.nombre,
                'modalidad': esp.modalidad.nombre
            })
        
        # Debug: verificar configuraciones existentes
        from config_institucional.models import EspecialidadCursoLectivo
        configuraciones_count = EspecialidadCursoLectivo.objects.filter(
            institucion=institucion,
            curso_lectivo=curso_lectivo,
            activa=True
        ).count()
        
        return JsonResponse({
            'success': True,
            'especialidades': especialidades_data,
            'curso_lectivo': curso_lectivo.nombre,
            'debug': {
                'institucion_id': institucion.id,
                'institucion_nombre': institucion.nombre,
                'curso_lectivo_id': curso_lectivo.id,
                'configuraciones_activas': configuraciones_count,
                'total_especialidades': len(especialidades_data)
            }
        })
        
    except CursoLectivo.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Curso lectivo no encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ════════════════════════════════════════════════════════════════
#                    DJANGO AUTOCOMPLETE LIGHT (DAL)
# ════════════════════════════════════════════════════════════════


class EspecialidadAutocomplete(autocomplete.Select2QuerySetView):
    """
    Autocompletado para Especialidad que filtra por Curso Lectivo, Nivel e institución.
    Solo muestra especialidades para niveles 10, 11, 12.
    Busca directamente en EspecialidadCursoLectivo.
    Forward: curso_lectivo, nivel → especialidad
    """
    def get_queryset(self):
        # DEBUG: Imprimir información de debug
        print("🔥 EspecialidadAutocomplete.get_queryset() llamado")
        
        if not self.request.user.is_authenticated:
            print("❌ Usuario no autenticado")
            return Especialidad.objects.none()
        
        print(f"👤 Usuario: {self.request.user.email} (superuser: {self.request.user.is_superuser})")
        
        # Obtener institución del usuario
        institucion_id = getattr(self.request, 'institucion_activa_id', None)
        print(f"🏢 Institución activa ID: {institucion_id}")
        
        if not institucion_id:
            # Para superusuario, usar institución 1 por defecto
            if self.request.user.is_superuser:
                institucion_id = 1
                print(f"👑 Superusuario - usando institución por defecto: {institucion_id}")
            else:
                print("❌ No hay institución activa")
                return Especialidad.objects.none()
        
        # FILTRO POR CURSO LECTIVO Y NIVEL (forward) - BUSCAR EN EspecialidadCursoLectivo
        curso_lectivo_id = self.forwarded.get('curso_lectivo', None)
        nivel_id = self.forwarded.get('nivel', None)
        print(f"📅 Curso lectivo ID: {curso_lectivo_id}")
        print(f"📊 Nivel ID: {nivel_id}")
        print(f"📅 Forwarded completo: {self.forwarded}")
        
        # Inicializar qs como None
        qs = None
        
        # REQUIERE tanto curso lectivo como nivel
        if curso_lectivo_id and nivel_id:
            try:
                from config_institucional.models import EspecialidadCursoLectivo
                from catalogos.models import Nivel
                
                # Verificar que el curso lectivo existe (ahora es global)
                curso_lectivo = CursoLectivo.objects.get(id=curso_lectivo_id)
                print(f"✅ Curso lectivo encontrado: {curso_lectivo.nombre}")
                
                # Verificar que el nivel existe
                nivel = Nivel.objects.get(id=nivel_id)
                print(f"✅ Nivel encontrado: {nivel}")
                
                # SOLO mostrar especialidades para niveles 10, 11, 12
                if nivel.numero not in [10, 11, 12]:
                    print(f"❌ Nivel {nivel.numero} ({nivel.nombre}) no requiere especialidad")
                    return Especialidad.objects.none()
                
                print(f"✅ Nivel {nivel.numero} ({nivel.nombre}) requiere especialidad")
                
                # Obtener especialidades configuradas y activas para este curso lectivo
                especialidades_configuradas = EspecialidadCursoLectivo.objects.filter(
                    institucion_id=institucion_id,
                    curso_lectivo=curso_lectivo,
                    activa=True
                ).values_list('especialidad_id', flat=True)
                
                print(f"🎯 Especialidades configuradas IDs: {list(especialidades_configuradas)}")
                
                # Filtrar especialidades
                qs = Especialidad.objects.filter(id__in=especialidades_configuradas)
                print(f"📋 Especialidades encontradas: {[esp.nombre for esp in qs]}")
                
            except (CursoLectivo.DoesNotExist, Nivel.DoesNotExist, ValueError) as e:
                print(f"❌ Error: {e}")
                return Especialidad.objects.none()
        else:
            # Sin curso lectivo o nivel, no mostrar especialidades
            if not curso_lectivo_id:
                print("❌ No hay curso lectivo seleccionado")
            if not nivel_id:
                print("❌ No hay nivel seleccionado")
            return Especialidad.objects.none()
        
        # Verificar que qs esté definido
        if qs is None:
            print("❌ qs no está definido")
            return Especialidad.objects.none()
        
        # Filtro por búsqueda
        if self.q:
            qs = qs.filter(nombre__icontains=self.q)
            print(f"🔍 Filtrado por búsqueda '{self.q}': {[esp.nombre for esp in qs]}")
        
        final_qs = qs.order_by('nombre')
        print(f"🎯 RESULTADO FINAL: {[esp.nombre for esp in final_qs]}")
        return final_qs


class SeccionAutocomplete(autocomplete.Select2QuerySetView):
    """
    Autocompletado para Sección que filtra por Curso Lectivo e institución.
    Busca directamente en SeccionCursoLectivo.
    Forward: curso_lectivo → seccion
    """
    def get_queryset(self):
        print("🔥 SeccionAutocomplete.get_queryset() llamado")
        
        if not self.request.user.is_authenticated:
            print("❌ Usuario no autenticado")
            return Seccion.objects.none()
        
        print(f"👤 Usuario: {self.request.user.email} (superuser: {self.request.user.is_superuser})")
        
        # Obtener institución del usuario
        institucion_id = getattr(self.request, 'institucion_activa_id', None)
        print(f"🏢 Institución activa ID: {institucion_id}")
        
        if not institucion_id:
            # Para superusuario, usar institución 1 por defecto
            if self.request.user.is_superuser:
                institucion_id = 1
                print(f"👑 Superusuario - usando institución por defecto: {institucion_id}")
            else:
                print("❌ No hay institución activa")
                return Seccion.objects.none()
        
        # FILTRO POR CURSO LECTIVO Y NIVEL (forward) - BUSCAR EN SeccionCursoLectivo
        curso_lectivo_id = self.forwarded.get('curso_lectivo', None)
        nivel_id = self.forwarded.get('nivel', None)
        print(f"📅 Curso lectivo ID: {curso_lectivo_id}")
        print(f"📅 Nivel ID: {nivel_id}")
        print(f"📅 Forwarded completo: {self.forwarded}")
        
        if curso_lectivo_id and nivel_id:
            try:
                from config_institucional.models import SeccionCursoLectivo
                from catalogos.models import Nivel
                
                # Verificar que el curso lectivo existe (ahora es global)
                curso_lectivo = CursoLectivo.objects.get(id=curso_lectivo_id)
                print(f"✅ Curso lectivo encontrado: {curso_lectivo.nombre}")
                
                # Verificar que el nivel existe
                nivel = Nivel.objects.get(id=nivel_id)
                print(f"✅ Nivel encontrado: {nivel}")
                
                # Obtener secciones configuradas y activas para este curso lectivo
                secciones_configuradas = SeccionCursoLectivo.objects.filter(
                    institucion_id=institucion_id,
                    curso_lectivo=curso_lectivo,
                    activa=True
                ).values_list('seccion_id', flat=True)
                
                print(f"🎯 Secciones configuradas IDs: {list(secciones_configuradas)}")
                
                # Filtrar secciones por nivel
                qs = Seccion.objects.filter(
                    id__in=secciones_configuradas,
                    nivel=nivel
                )
                print(f"🎯 Nivel seleccionado: {nivel.nombre}")
                print(f"📋 Secciones encontradas para nivel {nivel.numero}: {[sec.numero for sec in qs]}")
                
            except (CursoLectivo.DoesNotExist, Nivel.DoesNotExist, ValueError) as e:
                print(f"❌ Error: {e}")
                return Seccion.objects.none()
        else:
            # Sin curso lectivo, no mostrar secciones
            print("❌ No hay curso lectivo seleccionado")
            return Seccion.objects.none()
        
        # Filtro por búsqueda
        if self.q:
            qs = qs.filter(numero__icontains=self.q)
            print(f"🔍 Filtrado por búsqueda '{self.q}': {[f'Sección {s.numero}' for s in qs]}")
        
        final_qs = qs.order_by('nivel__numero', 'numero')
        print(f"🎯 RESULTADO FINAL: {[f'Sección {s.numero} - {s.nivel.nombre}' for s in final_qs]}")
        return final_qs


class SubgrupoAutocomplete(autocomplete.Select2QuerySetView):
    """
    Autocompletado para Subgrupo que filtra por Curso Lectivo, Sección e institución.
    Busca directamente en SubgrupoCursoLectivo.
    Forward: curso_lectivo, seccion → subgrupo
    """
    def get_queryset(self):
        print("🔥 SubgrupoAutocomplete.get_queryset() llamado")
        
        if not self.request.user.is_authenticated:
            print("❌ Usuario no autenticado")
            return Subgrupo.objects.none()
        
        print(f"👤 Usuario: {self.request.user.email} (superuser: {self.request.user.is_superuser})")
        
        # Obtener institución del usuario
        institucion_id = getattr(self.request, 'institucion_activa_id', None)
        print(f"🏢 Institución activa ID: {institucion_id}")
        
        if not institucion_id:
            # Para superusuario, usar institución 1 por defecto
            if self.request.user.is_superuser:
                institucion_id = 1
                print(f"👑 Superusuario - usando institución por defecto: {institucion_id}")
            else:
                print("❌ No hay institución activa")
                return Subgrupo.objects.none()
        
        # FILTRO POR CURSO LECTIVO Y SECCIÓN (forward) - BUSCAR EN SubgrupoCursoLectivo
        curso_lectivo_id = self.forwarded.get('curso_lectivo', None)
        seccion_id = self.forwarded.get('seccion', None)
        print(f"📅 Curso lectivo ID: {curso_lectivo_id}")
        print(f"📍 Sección ID: {seccion_id}")
        print(f"📅 Forwarded completo: {self.forwarded}")
        
        if curso_lectivo_id and seccion_id:
            try:
                from config_institucional.models import SubgrupoCursoLectivo
                
                # Verificar que el curso lectivo existe (ahora es global)
                curso_lectivo = CursoLectivo.objects.get(id=curso_lectivo_id)
                print(f"✅ Curso lectivo encontrado: {curso_lectivo.nombre}")
                
                # Verificar que la sección existe
                seccion = Seccion.objects.get(id=seccion_id)
                print(f"✅ Sección encontrada: {seccion}")
                
                # Obtener subgrupos configurados y activos para este curso lectivo
                # que pertenezcan específicamente a la sección seleccionada
                subgrupos_configurados = SubgrupoCursoLectivo.objects.filter(
                    institucion_id=institucion_id,
                    curso_lectivo=curso_lectivo,
                    activa=True,
                    subgrupo__seccion=seccion  # FILTRO ADICIONAL: solo subgrupos de la sección seleccionada
                ).values_list('subgrupo_id', flat=True)
                
                print(f"🎯 Subgrupos configurados IDs para sección {seccion}: {list(subgrupos_configurados)}")
                
                # Filtrar subgrupos
                qs = Subgrupo.objects.filter(id__in=subgrupos_configurados)
                print(f"📋 Subgrupos encontrados: {[f'{s.letra} - Sección {s.seccion.numero}' for s in qs]}")
                
            except (CursoLectivo.DoesNotExist, Seccion.DoesNotExist, ValueError) as e:
                print(f"❌ Error: {e}")
                return Subgrupo.objects.none()
        else:
            # Sin curso lectivo o sección, no mostrar subgrupos
            if not curso_lectivo_id:
                print("❌ No hay curso lectivo seleccionado")
            if not seccion_id:
                print("❌ No hay sección seleccionada")
            return Subgrupo.objects.none()
        
        # Filtro por búsqueda
        if self.q:
            qs = qs.filter(letra__icontains=self.q)
            print(f"🔍 Filtrado por búsqueda '{self.q}': {[s.letra for s in qs]}")
        
        final_qs = qs.order_by('seccion__nivel__numero', 'seccion__numero', 'letra')
        print(f"🎯 RESULTADO FINAL: {[f'{s.letra} - Sección {s.seccion.numero}' for s in final_qs]}")
        return final_qs
