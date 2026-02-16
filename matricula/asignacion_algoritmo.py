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
            'institucion': institucion,
            'curso_lectivo': curso_lectivo,
            'estado__iexact': 'activo',
            'seccion__isnull': True,
            'subgrupo__isnull': True
        }
        
        if nivel:
            filtros['nivel'] = nivel
        
        matriculas = list(MatriculaAcademica.objects.filter(**filtros).select_related(
            'estudiante', 'nivel', 'especialidad'
        ).order_by('estudiante__primer_apellido', 'estudiante__segundo_apellido', 'estudiante__nombres'))
        
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

        # 5.1 DIVIDIR SUBGRUPOS PARA ESTUDIANTES SIN ESPECIALIDAD SEGÚN SU SECCIÓN (p. ej. 7-1 → 7-1A, 7-1B)
        # Para niveles sin especialidad (p. ej. 7º), si existen subgrupos configurados (sin especialidad) por sección,
        # repartir equitativamente los alumnos ya asignados a esa sección entre dichos subgrupos
        if asignaciones_secciones and subgrupos_disponibles:
            for seccion_id, matriculas_asignadas in asignaciones_secciones.items():
                # Subgrupos activos de esta sección y sin especialidad (niveles distintos a 10-12)
                subgrupos_seccion = [
                    s for s in subgrupos_disponibles
                    if getattr(s, 'especialidad_curso_id', None) in (None,)
                    and s.subgrupo.seccion.id == seccion_id
                ]
                if not subgrupos_seccion:
                    continue
                distribucion = dividir_matriculas_en_subgrupos(matriculas_asignadas, subgrupos_seccion)
                for sub_conf, mats in distribucion.items():
                    asignaciones_subgrupos.setdefault(sub_conf.subgrupo.id, []).extend(mats)
        
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
                
                # Asignar subgrupos (y su sección correspondiente)
                for subgrupo_id, matriculas_asignadas in asignaciones_subgrupos.items():
                    subgrupo = Subgrupo.objects.get(id=subgrupo_id)
                    for matricula in matriculas_asignadas:
                        matricula.subgrupo = subgrupo
                        # Asegurar coherencia: sección del subgrupo
                        matricula.seccion = subgrupo.seccion
                        matricula.save(update_fields=['subgrupo', 'seccion'])
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
    
    for especialidad_ecl_id, estudiantes in estudiantes_por_especialidad.items():
        # Encontrar subgrupos que manejen esta especialidad
        subgrupos_especialidad = [
            s for s in subgrupos_disponibles 
            # IMPORTANTE: comparar por ID de EspecialidadCursoLectivo (ECL), no por Especialidad
            if s.especialidad_curso and s.especialidad_curso_id == especialidad_ecl_id
        ]
        
        if not subgrupos_especialidad:
            continue
        
        # Agrupar por nivel (10, 11, 12) y distribuir primero por subgrupos de la especialidad
        estudiantes_por_nivel = defaultdict(list)
        for matricula in estudiantes:
            estudiantes_por_nivel[matricula.nivel.id].append(matricula)

        for nivel_id, estudiantes_nivel in estudiantes_por_nivel.items():
            # Subgrupos de este nivel y especialidad
            subgrupos_nivel = [s for s in subgrupos_especialidad if s.subgrupo.seccion.nivel_id == nivel_id]
            if not subgrupos_nivel:
                continue

            # Distribuir equitativamente por subgrupo (con nuestra lógica por género/apellidos)
            asignaciones_nivel, hermanos_nivel = distribuir_estudiantes_equitativamente(
                estudiantes_nivel,
                subgrupos_nivel,
                'subgrupo'
            )

            # Agregar al resultado con subgrupo → y luego sección se coloca al aplicar (subgrupo.seccion)
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
    
    # 2. OBJETIVO DE TAMAÑO POR GRUPO (equidistribución y tope 32)
    objetivos_tamano = distribuir_objetivo(total_estudiantes, num_grupos)
    # Verificación de capacidad máxima por grupo (32) — si es inviable, se permitirá overflow mínimo
    capacidad_maxima = [min(32, objetivo) if total_estudiantes <= num_grupos * 32 else 32 for objetivo in objetivos_tamano]

    # 3. AGRUPAR POR APELLIDOS (HERMANOS) Y PREPARAR LISTAS POR GÉNERO
    clusters_hermanos = defaultdict(list)
    for matricula in estudiantes:
        clave_hermanos = generar_clave_hermanos(matricula.estudiante)
        clusters_hermanos[clave_hermanos].append(matricula)

    # Listas por género, ordenadas alfabéticamente por apellidos (clave del cluster)
    mujeres = []
    hombres = []
    otros = []
    for clave, cluster in clusters_hermanos.items():
        # ordenar cluster internamente por nombres para estabilidad
        cluster_ordenado = sorted(cluster, key=lambda m: (m.estudiante.nombres or '').upper())
        for m in cluster_ordenado:
            genero_key = determinar_genero_key(m.estudiante)
            if genero_key == 'F':
                mujeres.append((clave, m))
            elif genero_key == 'M':
                hombres.append((clave, m))
            else:
                otros.append((clave, m))

    mujeres.sort(key=lambda x: (x[0][0], x[0][1]))
    hombres.sort(key=lambda x: (x[0][0], x[0][1]))
    otros.sort(key=lambda x: (x[0][0], x[0][1]))

    # 4. INICIALIZAR ASIGNACIONES Y CONTADORES
    asignaciones = {grupo: [] for grupo in grupos_disponibles}
    contadores_genero = {grupo: {'F': 0, 'M': 0, 'O': 0} for grupo in grupos_disponibles}
    cluster_objetivo = {}  # mapa de clave_hermanos -> grupo elegido
    rr_idx = 0  # round-robin index

    def elegir_grupo_para_primero_de_cluster(tamano_cluster):
        nonlocal rr_idx
        # Preferir grupo bajo objetivo de tamaño
        for paso in (0, 1):
            # paso 0: <= objetivo; paso 1: <= capacidad máxima
            limite_lista = objetivos_tamano if paso == 0 else capacidad_maxima
            for intento in range(num_grupos):
                i = (rr_idx + intento) % num_grupos
                grupo = grupos_disponibles[i]
                if len(asignaciones[grupo]) + tamano_cluster <= limite_lista[i]:
                    rr_idx = (i + 1) % num_grupos
                    return grupo
        # Si no hay espacio bajo límites, seleccionar el grupo con menor carga actual
        i_min = min(range(num_grupos), key=lambda j: len(asignaciones[grupos_disponibles[j]]))
        grupo = grupos_disponibles[i_min]
        rr_idx = (i_min + 1) % num_grupos
        return grupo

    def asignar_estudiante(clave, matricula):
        # Forzar el grupo del cluster si ya existe
        if clave in cluster_objetivo:
            grupo = cluster_objetivo[clave]
        else:
            # Elegir grupo para el primer miembro del cluster
            tamano_cluster = len(clusters_hermanos.get(clave, [matricula]))
            grupo = elegir_grupo_para_primero_de_cluster(tamano_cluster)
            cluster_objetivo[clave] = grupo
        asignaciones[grupo].append(matricula)
        genero_key = determinar_genero_key(matricula.estudiante)
        contadores_genero[grupo][genero_key] += 1

    # 5. ASIGNAR EN ORDEN: MUJERES → HOMBRES → OTROS (round-robin al elegir primer miembro de cada cluster)
    for clave, m in mujeres:
        asignar_estudiante(clave, m)
    for clave, m in hombres:
        asignar_estudiante(clave, m)
    for clave, m in otros:
        asignar_estudiante(clave, m)

    # 6. Calcular hermanos_count (cantidad de integrantes en clusters con tamaño > 1)
    hermanos_count = sum(len(cluster) for cluster in clusters_hermanos.values() if len(cluster) > 1)

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
                                     composicion_cluster, obj_f, obj_m, obj_o, objetivos_tamano, capacidad_maxima):
    """
    Encuentra el mejor grupo para asignar un cluster de hermanos.
    """
    mejor_grupo = None
    mejor_score = float('inf')
    
    # Primer intento: respetar estrictamente objetivos de tamaño (no pasar del objetivo)
    indices_evaluacion = list(range(len(grupos_disponibles)))

    # Preferir grupos con espacio real respecto al objetivo de tamaño
    grupos_con_espacio = [i for i in indices_evaluacion if (len(asignaciones[grupos_disponibles[i]]) + sum(composicion_cluster.values())) <= objetivos_tamano[i]]
    candidatos = grupos_con_espacio if grupos_con_espacio else indices_evaluacion

    for i in candidatos:
        grupo = grupos_disponibles[i]
        # No exceder capacidad máxima dura (32) salvo que sea inviable; si todos exceden, se evaluará de todas formas
        if grupos_con_espacio and (len(asignaciones[grupo]) + sum(composicion_cluster.values())) > capacidad_maxima[i]:
            continue
        # Calcular score si asignáramos este cluster aquí
        score = calcular_score_asignacion(
            contadores_genero[grupo],
            composicion_cluster,
            obj_f[i],
            obj_m[i], 
            obj_o[i],
            len(asignaciones[grupo]),
            i,  # índice del grupo para desempate
            objetivos_tamano[i]
        )
        
        if score < mejor_score:
            mejor_score = score
            mejor_grupo = grupo
    
    return mejor_grupo


def calcular_score_asignacion(contador_actual, composicion_cluster, obj_f, obj_m, obj_o, total_actual, indice_grupo, objetivo_tamano):
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
    desv_tamano = abs(nuevo_total - objetivo_tamano)
    
    # Score combinado con pesos
    # 1000: equilibrio de género (máxima prioridad)
    # 200: cercanía al objetivo de tamaño (evita sobrecupo o subcupo)
    # 1: índice de grupo (desempate determinístico)
    score = (desv_f * 1000) + (desv_m * 1000) + (desv_o * 1000) + (desv_tamano * 200) + indice_grupo
    
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


def dividir_matriculas_en_subgrupos(matriculas, subgrupos_config):
    """Divide una lista de matrículas en los subgrupos dados de forma equitativa y estable.
    - Ordena subgrupos por letra (A, B, C, ...)
    - Ordena matrículas alfabéticamente por apellidos y nombres
    - Asigna por bloques consecutivos según objetivos (p. ej. primeros 16 a A, siguientes 16 a B)
    """
    if not subgrupos_config:
        return {}
    subgrupos_ordenados = sorted(subgrupos_config, key=lambda s: (s.subgrupo.seccion.nivel.numero, s.subgrupo.seccion.numero, s.subgrupo.letra))
    objetivos = distribuir_objetivo(len(matriculas), len(subgrupos_ordenados))
    # Orden alfabético de estudiantes dentro de la sección
    matriculas_ordenadas = sorted(
        matriculas,
        key=lambda m: (
            (m.estudiante.primer_apellido or '').upper(),
            (m.estudiante.segundo_apellido or '').upper(),
            (m.estudiante.nombres or '').upper(),
        )
    )
    asignaciones = {sub: [] for sub in subgrupos_ordenados}
    start = 0
    for i, sub in enumerate(subgrupos_ordenados):
        end = start + objetivos[i]
        if start < len(matriculas_ordenadas):
            asignaciones[sub].extend(matriculas_ordenadas[start:end])
        start = end
    return asignaciones
