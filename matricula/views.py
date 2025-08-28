from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from config_institucional.models import Nivel
from catalogos.models import CursoLectivo, Seccion, Subgrupo, Especialidad
from core.models import Institucion
from .models import Estudiante, MatriculaAcademica, PlantillaImpresionMatricula
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
    
    # Obtener la plantilla de impresión específica de la institución
    plantilla = None
    if request.user.is_superuser:
        # Superusuario: obtener plantilla según institución seleccionada
        institucion_id = request.POST.get('institucion') if request.method == 'POST' else None
        if institucion_id:
            try:
                institucion_temp = Institucion.objects.get(pk=institucion_id)
                plantilla = PlantillaImpresionMatricula.objects.filter(institucion=institucion_temp).first()
            except:
                pass
    else:
        # Usuario normal: obtener plantilla de su institución activa
        institucion_id = getattr(request, 'institucion_activa_id', None)
        if institucion_id:
            try:
                plantilla = PlantillaImpresionMatricula.objects.filter(institucion_id=institucion_id).first()
            except:
                pass
    
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
                            'plantilla': plantilla,
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
                        years = today.year - estudiante.fecha_nacimiento.year
                        months = today.month - estudiante.fecha_nacimiento.month
                        
                        # Ajustar si el mes actual es menor que el mes de nacimiento
                        if months < 0:
                            years -= 1
                            months += 12
                        
                        # Formatear la edad
                        if years == 0:
                            edad_estudiante = f"{months} meses"
                        elif months == 0:
                            edad_estudiante = f"{years} años"
                        else:
                            edad_estudiante = f"{years} años y {months} meses"
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
                # Log del error para debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error inesperado en consulta_estudiante: {e}")
                error = 'Error interno del sistema. Contacte al administrador.'
    
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
        'plantilla': plantilla,
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
        
        # Obtener curso lectivo (es GLOBAL, no tiene institucion_id)
        from core.models import Institucion
        curso_lectivo = CursoLectivo.objects.get(id=curso_lectivo_id)
        institucion = Institucion.objects.get(id=institucion_id)
        
        # Obtener especialidades disponibles
        especialidades_disponibles = MatriculaAcademica.get_especialidades_disponibles(
            institucion=institucion,
            curso_lectivo=curso_lectivo
        )
        
        # Preparar datos para JSON
        especialidades_data = []
        for ecl in especialidades_disponibles:
            # ecl es EspecialidadCursoLectivo; extraer la especialidad real
            if hasattr(ecl, 'especialidad') and ecl.especialidad:
                especialidades_data.append({
                    'id': ecl.especialidad.id,
                    'nombre': ecl.especialidad.nombre,
                    'modalidad': getattr(getattr(ecl.especialidad, 'modalidad', None), 'nombre', '')
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
    except Institucion.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Institución no encontrada'})
    except Exception as e:
        # Log del error para debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error inesperado en get_especialidades_disponibles: {e}")
        return JsonResponse({'success': False, 'error': 'Error interno del sistema'})



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
                qs = EspecialidadCursoLectivo.objects.filter(
                    institucion_id=institucion_id,
                    curso_lectivo=curso_lectivo,
                    activa=True
                ).select_related('especialidad', 'especialidad__modalidad')
                
                print(f"🎯 Especialidades configuradas encontradas: {[ecl.especialidad.nombre for ecl in qs]}")
                print(f"📋 Especialidades encontradas: {[ecl.especialidad.nombre for ecl in qs]}")
                
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
            qs = qs.filter(especialidad__nombre__icontains=self.q)
            print(f"🔍 Filtrado por búsqueda '{self.q}': {[ecl.especialidad.nombre for ecl in qs]}")
        
        final_qs = qs.order_by('especialidad__nombre')
        print(f"🎯 RESULTADO FINAL: {[ecl.especialidad.nombre for ecl in final_qs]}")
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


# ════════════════════════════════════════════════════════════════
#                    ASIGNACIÓN AUTOMÁTICA DE GRUPOS
# ════════════════════════════════════════════════════════════════

@login_required
def asignacion_grupos(request):
    """
    Vista principal para la asignación automática de grupos.
    """
    from catalogos.models import CursoLectivo, Nivel
    from core.models import Institucion
    from .models import AsignacionGrupos
    
    context = {
        'instituciones': Institucion.objects.all().order_by('nombre') if request.user.is_superuser else [],
        'cursos_lectivos': CursoLectivo.objects.all().order_by('-anio'),
        'niveles': Nivel.objects.all().order_by('numero'),
        'es_superusuario': request.user.is_superuser,
        'asignaciones_recientes': AsignacionGrupos.objects.filter(
            institucion_id=getattr(request, 'institucion_activa_id', None) if not request.user.is_superuser else None
        ).order_by('-fecha_asignacion')[:10]
    }
    
    return render(request, 'matricula/asignacion_grupos.html', context)


@login_required
def ejecutar_asignacion_grupos(request):
    """
    Vista AJAX que ejecuta el algoritmo de asignación automática de grupos.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        # Obtener parámetros
        curso_lectivo_id = request.POST.get('curso_lectivo_id')
        nivel_id = request.POST.get('nivel_id')
        simular = request.POST.get('simular', 'false').lower() == 'true'
        
        # Validar parámetros requeridos
        if not curso_lectivo_id:
            return JsonResponse({'success': False, 'error': 'Curso lectivo es requerido'})
        
        # Obtener institución
        if request.user.is_superuser:
            institucion_id = request.POST.get('institucion_id')
            if not institucion_id:
                return JsonResponse({'success': False, 'error': 'Institución es requerida para superusuarios'})
            institucion = Institucion.objects.get(id=institucion_id)
        else:
            institucion_id = getattr(request, 'institucion_activa_id', None)
            if not institucion_id:
                return JsonResponse({'success': False, 'error': 'No se pudo determinar la institución activa'})
            institucion = Institucion.objects.get(id=institucion_id)
        
        # Obtener objetos
        from catalogos.models import CursoLectivo, Nivel
        curso_lectivo = CursoLectivo.objects.get(id=curso_lectivo_id)
        nivel = Nivel.objects.get(id=nivel_id) if nivel_id else None
        
        # Ejecutar algoritmo
        from .asignacion_algoritmo import ejecutar_asignacion_completa
        resultado = ejecutar_asignacion_completa(
            institucion=institucion,
            curso_lectivo=curso_lectivo,
            nivel=nivel,
            usuario=request.user,
            simular=simular
        )
        
        return JsonResponse(resultado)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error en ejecutar_asignacion_grupos: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Error interno: {str(e)}'})
