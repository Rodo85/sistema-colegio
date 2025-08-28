"""
Algoritmo de asignación automática de grupos para estudiantes.

Implementa la lógica completa de distribución equitativa considerando:
- Equilibrio por género (F/M/O)
- Orden alfabético por primer apellido
- Hermanos juntos (mismo primer y segundo apellido)
- Round-robin ponderado para distribución equitativa
- Separación por especialidad vs sin especialidad
"""

from collections import defaultdict, Counter
from django.db import transaction
import math


def ejecutar_asignacion_completa(institucion, curso_lectivo, nivel, usuario, simular=False):
    """
    Función principal que ejecuta la asignación automática completa.
    
    Args:
        institucion: Objeto Institucion
        curso_lectivo: Objeto CursoLectivo
        nivel: Objeto Nivel (opcional, None para todos los niveles)
        usuario: Usuario que ejecuta la asignación
        simular: Si True, no guarda cambios, solo simula
    
    Returns:
        dict: Resultado con estadísticas y detalles de la asignación
    """
    from .models import MatriculaAcademica, AsignacionGrupos
    from config_institucional.models import SeccionCursoLectivo, SubgrupoCursoLectivo
    from catalogos.models import Seccion, Subgrupo
    
    resultado = {
        'success': False,
        'mensaje': '',
        'estadisticas': {},
        'detalle_asignaciones': [],
        'errores': []
    }
    
    try:
        # 1. OBTENER ESTUDIANTES ELEGIBLES
        filtros = {
            'estudiante__institucion': institucion,
            'curso_lectivo': curso_lectivo,
            'estado__iexact': 'activo',
            'seccion__isnull': True,
            'subgrupo__isnull': True
        }
        
        if nivel:
            filtros['nivel'] = nivel
        
        matriculas = list(MatriculaAcademica.objects.filter(**filtros).select_related(
            'estudiante', 'nivel', 'especialidad'
        ).order_by('estudiante__primer_apellido', 'estudiante__segundo_apellido', 'estudiante__primer_nombre'))
        
        if not matriculas:
            resultado['mensaje'] = 'No hay estudiantes elegibles para asignar'
            return resultado
        
        # 2. OBTENER SECCIONES Y SUBGRUPOS DISPONIBLES
        if nivel:
            # Filtrar por nivel específico
            secciones_disponibles = SeccionCursoLectivo.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
                seccion__nivel=nivel,
                activa=True
            ).select_related('seccion').order_by('seccion__numero')
            
            subgrupos_disponibles = SubgrupoCursoLectivo.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
                subgrupo__seccion__nivel=nivel,
                activa=True
            ).select_related('subgrupo', 'especialidad_curso').order_by('subgrupo__letra')
        else:
            # Todos los niveles
            secciones_disponibles = SeccionCursoLectivo.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
                activa=True
            ).select_related('seccion').order_by('seccion__nivel__numero', 'seccion__numero')
            
            subgrupos_disponibles = SubgrupoCursoLectivo.objects.filter(
                institucion=institucion,
                curso_lectivo=curso_lectivo,
                activa=True
            ).select_related('subgrupo', 'especialidad_curso').order_by('subgrupo__seccion__nivel__numero', 'subgrupo__letra')
        
        # 3. SEPARAR POR ESPECIALIDAD Y SIN ESPECIALIDAD
        estudiantes_sin_especialidad = []
        estudiantes_con_especialidad = defaultdict(list)  # {especialidad_id: [matriculas]}
        
        for matricula in matriculas:
            if matricula.especialidad:
                estudiantes_con_especialidad[matricula.especialidad.id].append(matricula)
            else:
                estudiantes_sin_especialidad.append(matricula)
        
        # 4. PROCESAR ESTUDIANTES SIN ESPECIALIDAD
        asignaciones_secciones = {}
        hermanos_secciones = 0
        if estudiantes_sin_especialidad and secciones_disponibles:
            asignaciones_secciones, hermanos_secciones = procesar_estudiantes_sin_especialidad(
                estudiantes_sin_especialidad, 
                secciones_disponibles
            )
        
        # 5. PROCESAR ESTUDIANTES CON ESPECIALIDAD
        asignaciones_subgrupos = {}
        hermanos_subgrupos = 0
        if estudiantes_con_especialidad and subgrupos_disponibles:
            asignaciones_subgrupos, hermanos_subgrupos = procesar_estudiantes_con_especialidad(
                estudiantes_con_especialidad,
                subgrupos_disponibles
            )
        
        # 6. APLICAR ASIGNACIONES (solo si no es simulación)
        total_asignados = 0
        if not simular:
            with transaction.atomic():
                # Asignar secciones
                for seccion_id, matriculas_asignadas in asignaciones_secciones.items():
                    seccion = Seccion.objects.get(id=seccion_id)
                    for matricula in matriculas_asignadas:
                        matricula.seccion = seccion
                        matricula.save(update_fields=['seccion'])
                        total_asignados += 1
                
                # Asignar subgrupos
                for subgrupo_id, matriculas_asignadas in asignaciones_subgrupos.items():
                    subgrupo = Subgrupo.objects.get(id=subgrupo_id)
                    for matricula in matriculas_asignadas:
                        matricula.subgrupo = subgrupo
                        matricula.save(update_fields=['subgrupo'])
                        total_asignados += 1
                
                # Crear registro de asignación
                if total_asignados > 0:
                    stats = calcular_estadisticas_completas(matriculas)
                    AsignacionGrupos.objects.create(
                        institucion=institucion,
                        curso_lectivo=curso_lectivo,
                        nivel=nivel,
                        usuario_asignacion=usuario,
                        total_estudiantes=total_asignados,
                        total_mujeres=stats['mujeres'],
                        total_hombres=stats['hombres'],
                        total_otros=stats['otros'],
                        secciones_utilizadas=len(asignaciones_secciones),
                        subgrupos_utilizados=len(asignaciones_subgrupos),
                        hermanos_agrupados=hermanos_secciones + hermanos_subgrupos,
                        observaciones=f"Asignación automática: {len(asignaciones_secciones)} secciones, {len(asignaciones_subgrupos)} subgrupos"
                    )
        else:
            # Simulación: solo contar
            total_asignados = sum(len(m) for m in asignaciones_secciones.values())
            total_asignados += sum(len(m) for m in asignaciones_subgrupos.values())
        
        # 7. PREPARAR RESULTADO
        resultado['success'] = True
        resultado['mensaje'] = f"{'Simulación completada' if simular else 'Asignación completada'}: {total_asignados} estudiantes asignados"
        resultado['estadisticas'] = {
            'total_estudiantes': len(matriculas),
            'total_asignados': total_asignados,
            'secciones_utilizadas': len(asignaciones_secciones),
            'subgrupos_utilizados': len(asignaciones_subgrupos),
            'estudiantes_sin_especialidad': len(estudiantes_sin_especialidad),
            'estudiantes_con_especialidad': sum(len(v) for v in estudiantes_con_especialidad.values()),
            'hermanos_agrupados': hermanos_secciones + hermanos_subgrupos
        }
        
        # Agregar detalles de las asignaciones
        resultado['detalle_asignaciones'] = generar_detalle_asignaciones(
            asignaciones_secciones, asignaciones_subgrupos
        )
        
        return resultado
        
    except Exception as e:
        resultado['errores'].append(f"Error general: {str(e)}")
        return resultado


def procesar_estudiantes_sin_especialidad(estudiantes, secciones_disponibles):
    """
    Procesa estudiantes sin especialidad y los asigna a secciones.
    
    Returns:
        tuple: (asignaciones_dict, hermanos_count)
    """
    # Agrupar por nivel
    estudiantes_por_nivel = defaultdict(list)
    for matricula in estudiantes:
        estudiantes_por_nivel[matricula.nivel.id].append(matricula)
    
    asignaciones_finales = defaultdict(list)
    total_hermanos = 0
    
    for nivel_id, estudiantes_nivel in estudiantes_por_nivel.items():
        # Obtener secciones para este nivel
        secciones_nivel = [s for s in secciones_disponibles if s.seccion.nivel_id == nivel_id]
        
        if not secciones_nivel:
            continue
        
        # Aplicar algoritmo de distribución
        asignaciones_nivel, hermanos_nivel = distribuir_estudiantes_equitativamente(
            estudiantes_nivel, 
            secciones_nivel, 
            'seccion'
        )
        
        # Agregar al resultado
        for seccion_config, matriculas in asignaciones_nivel.items():
            asignaciones_finales[seccion_config.seccion.id].extend(matriculas)
        
        total_hermanos += hermanos_nivel
    
    return dict(asignaciones_finales), total_hermanos


def procesar_estudiantes_con_especialidad(estudiantes_por_especialidad, subgrupos_disponibles):
    """
    Procesa estudiantes con especialidad y los asigna a subgrupos.
    
    Returns:
        tuple: (asignaciones_dict, hermanos_count)
    """
    asignaciones_finales = defaultdict(list)
    total_hermanos = 0
    
    for especialidad_id, estudiantes in estudiantes_por_especialidad.items():
        # Encontrar subgrupos que manejen esta especialidad
        subgrupos_especialidad = [
            s for s in subgrupos_disponibles 
            if s.especialidad_curso and s.especialidad_curso.especialidad_id == especialidad_id
        ]
        
        if not subgrupos_especialidad:
            continue
        
        # Agrupar por nivel
        estudiantes_por_nivel = defaultdict(list)
        for matricula in estudiantes:
            estudiantes_por_nivel[matricula.nivel.id].append(matricula)
        
        for nivel_id, estudiantes_nivel in estudiantes_por_nivel.items():
            # Subgrupos de este nivel y especialidad
            subgrupos_nivel = [s for s in subgrupos_especialidad if s.subgrupo.seccion.nivel_id == nivel_id]
            
            if not subgrupos_nivel:
                continue
            
            # Aplicar algoritmo de distribución
            asignaciones_nivel, hermanos_nivel = distribuir_estudiantes_equitativamente(
                estudiantes_nivel, 
                subgrupos_nivel, 
                'subgrupo'
            )
            
            # Agregar al resultado
            for subgrupo_config, matriculas in asignaciones_nivel.items():
                asignaciones_finales[subgrupo_config.subgrupo.id].extend(matriculas)
            
            total_hermanos += hermanos_nivel
    
    return dict(asignaciones_finales), total_hermanos


def distribuir_estudiantes_equitativamente(estudiantes, grupos_disponibles, tipo_grupo):
    """
    Algoritmo principal de distribución equitativa de estudiantes.
    
    Args:
        estudiantes: Lista de MatriculaAcademica
        grupos_disponibles: Lista de SeccionCursoLectivo o SubgrupoCursoLectivo
        tipo_grupo: 'seccion' o 'subgrupo'
    
    Returns:
        tuple: (asignaciones_dict, hermanos_count)
    """
    if not grupos_disponibles:
        return {}, 0
    
    num_grupos = len(grupos_disponibles)
    total_estudiantes = len(estudiantes)
    
    # 1. CALCULAR OBJETIVOS POR GÉNERO
    generos = Counter(determinar_genero_key(e.estudiante) for e in estudiantes)
    mujeres = generos.get('F', 0)
    hombres = generos.get('M', 0)
    otros = generos.get('O', 0)
    
    # Distribución objetivo por grupo
    objetivos_mujeres = distribuir_objetivo(mujeres, num_grupos)
    objetivos_hombres = distribuir_objetivo(hombres, num_grupos) 
    objetivos_otros = distribuir_objetivo(otros, num_grupos)
    
    # 2. AGRUPAR POR APELLIDOS (HERMANOS)
    clusters_hermanos = defaultdict(list)
    for matricula in estudiantes:
        clave_hermanos = generar_clave_hermanos(matricula.estudiante)
        clusters_hermanos[clave_hermanos].append(matricula)
    
    # 3. ORDENAR CLUSTERS ALFABÉTICAMENTE
    clusters_ordenados = sorted(clusters_hermanos.items(), key=lambda x: x[0])
    
    # 4. INICIALIZAR ASIGNACIONES
    asignaciones = {grupo: [] for grupo in grupos_disponibles}
    contadores_genero = {
        grupo: {'F': 0, 'M': 0, 'O': 0} 
        for grupo in grupos_disponibles
    }
    
    # 5. ASIGNAR CLUSTERS USANDO ROUND-ROBIN PONDERADO
    hermanos_count = 0
    for (apellidos, cluster) in clusters_ordenados:
        # Contar hermanos (clusters con más de 1 estudiante)
        if len(cluster) > 1:
            hermanos_count += len(cluster)
        
        # Determinar composición del cluster por género
        composicion_cluster = Counter()
        for matricula in cluster:
            genero_key = determinar_genero_key(matricula.estudiante)
            composicion_cluster[genero_key] += 1
        
        # Encontrar el mejor grupo para este cluster
        mejor_grupo = encontrar_mejor_grupo_para_cluster(
            grupos_disponibles,
            contadores_genero,
            asignaciones,
            composicion_cluster,
            objetivos_mujeres,
            objetivos_hombres,
            objetivos_otros
        )
        
        # Asignar cluster al mejor grupo
        if mejor_grupo:
            asignaciones[mejor_grupo].extend(cluster)
            for matricula in cluster:
                genero_key = determinar_genero_key(matricula.estudiante)
                contadores_genero[mejor_grupo][genero_key] += 1
    
    return asignaciones, hermanos_count


def distribuir_objetivo(total, num_grupos):
    """Distribuye un total entre grupos de manera equitativa."""
    base = total // num_grupos
    extras = total % num_grupos
    
    objetivos = [base] * num_grupos
    for i in range(extras):
        objetivos[i] += 1
    
    return objetivos


def generar_clave_hermanos(estudiante):
    """Genera una clave única para identificar hermanos."""
    return (
        (estudiante.primer_apellido or '').upper(),
        (estudiante.segundo_apellido or '').upper()
    )


def determinar_genero_key(estudiante):
    """Determina la clave de género estandarizada."""
    if not estudiante.sexo:
        return 'O'
    sexo = estudiante.sexo.nombre.upper()
    if sexo in ['FEMENINO', 'F', 'MUJER']:
        return 'F'
    elif sexo in ['MASCULINO', 'M', 'HOMBRE']:
        return 'M'
    else:
        return 'O'


def encontrar_mejor_grupo_para_cluster(grupos_disponibles, contadores_genero, asignaciones, 
                                     composicion_cluster, obj_f, obj_m, obj_o):
    """
    Encuentra el mejor grupo para asignar un cluster de hermanos.
    """
    mejor_grupo = None
    mejor_score = float('inf')
    
    for i, grupo in enumerate(grupos_disponibles):
        # Calcular score si asignáramos este cluster aquí
        score = calcular_score_asignacion(
            contadores_genero[grupo],
            composicion_cluster,
            obj_f[i],
            obj_m[i], 
            obj_o[i],
            len(asignaciones[grupo]),
            i  # índice del grupo para desempate
        )
        
        if score < mejor_score:
            mejor_score = score
            mejor_grupo = grupo
    
    return mejor_grupo


def calcular_score_asignacion(contador_actual, composicion_cluster, obj_f, obj_m, obj_o, total_actual, indice_grupo):
    """
    Calcula un score para determinar qué tan buena sería una asignación.
    Score más bajo = mejor asignación.
    """
    # Simular la asignación
    nuevo_f = contador_actual['F'] + composicion_cluster.get('F', 0)
    nuevo_m = contador_actual['M'] + composicion_cluster.get('M', 0) 
    nuevo_o = contador_actual['O'] + composicion_cluster.get('O', 0)
    nuevo_total = total_actual + sum(composicion_cluster.values())
    
    # Calcular desviaciones de los objetivos (prioridad alta)
    desv_f = abs(nuevo_f - obj_f)
    desv_m = abs(nuevo_m - obj_m)
    desv_o = abs(nuevo_o - obj_o)
    
    # Score combinado con pesos
    # 1000: equilibrio de género (máxima prioridad)
    # 10: total de estudiantes por grupo
    # 1: índice de grupo (desempate determinístico)
    score = (desv_f * 1000) + (desv_m * 1000) + (desv_o * 1000) + (nuevo_total * 10) + indice_grupo
    
    return score


def calcular_estadisticas_completas(matriculas):
    """Calcula estadísticas completas de la asignación."""
    generos = Counter()
    
    for matricula in matriculas:
        # Contar géneros
        genero_key = determinar_genero_key(matricula.estudiante)
        generos[genero_key] += 1
    
    return {
        'mujeres': generos.get('F', 0),
        'hombres': generos.get('M', 0),
        'otros': generos.get('O', 0)
    }


def generar_detalle_asignaciones(asignaciones_secciones, asignaciones_subgrupos):
    """Genera un detalle legible de las asignaciones realizadas."""
    from catalogos.models import Seccion, Subgrupo
    
    detalles = []
    
    # Detalles de secciones
    for seccion_id, matriculas in asignaciones_secciones.items():
        try:
            seccion = Seccion.objects.get(id=seccion_id)
            generos = Counter(determinar_genero_key(m.estudiante) for m in matriculas)
            
            detalles.append({
                'tipo': 'seccion',
                'nombre': f"Sección {seccion.numero} - {seccion.nivel.nombre}",
                'total': len(matriculas),
                'mujeres': generos.get('F', 0),
                'hombres': generos.get('M', 0),
                'otros': generos.get('O', 0)
            })
        except Seccion.DoesNotExist:
            continue
    
    # Detalles de subgrupos
    for subgrupo_id, matriculas in asignaciones_subgrupos.items():
        try:
            subgrupo = Subgrupo.objects.get(id=subgrupo_id)
            generos = Counter(determinar_genero_key(m.estudiante) for m in matriculas)
            
            detalles.append({
                'tipo': 'subgrupo',
                'nombre': f"Subgrupo {subgrupo.letra} - Sección {subgrupo.seccion.numero} - {subgrupo.seccion.nivel.nombre}",
                'total': len(matriculas),
                'mujeres': generos.get('F', 0),
                'hombres': generos.get('M', 0),
                'otros': generos.get('O', 0)
            })
        except Subgrupo.DoesNotExist:
            continue
    
    return sorted(detalles, key=lambda x: x['nombre'])
