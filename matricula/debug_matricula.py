"""
Herramientas de debugging para el sistema de matrícula
"""
import logging
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

def debug_especialidades_estudiante(estudiante, curso_lectivo):
    """
    Función de debugging para verificar especialidades disponibles
    """
    try:
        from .models import MatriculaAcademica
        
        print(f"🔍 DEBUG: Verificando especialidades para {estudiante}")
        print(f"   📚 Estudiante: {estudiante.identificacion} - {estudiante.nombres}")
        print(f"   🏢 Institución: {estudiante.institucion.nombre}")
        print(f"   📅 Curso lectivo: {curso_lectivo.nombre}")
        
        # Obtener especialidades disponibles
        especialidades = MatriculaAcademica.get_especialidades_disponibles(
            institucion=estudiante.institucion,
            curso_lectivo=curso_lectivo
        )
        
        print(f"   🎯 Especialidades disponibles: {especialidades.count()}")
        for esp in especialidades:
            print(f"      - {esp.especialidad.nombre} ({esp.especialidad.modalidad.nombre})")
        
        # Verificar matrículas previas
        matriculas_previas = MatriculaAcademica.objects.filter(
            estudiante=estudiante,
            estado='activo'
        ).order_by('-curso_lectivo__anio')
        
        print(f"   📋 Matrículas previas: {matriculas_previas.count()}")
        for mat in matriculas_previas:
            print(f"      - {mat.curso_lectivo.nombre}: {mat.nivel.nombre} - {mat.especialidad.especialidad.nombre if mat.especialidad else 'Sin especialidad'}")
        
        return especialidades
        
    except Exception as e:
        logger.error(f"Error en debug_especialidades_estudiante: {e}")
        print(f"❌ Error: {e}")
        return None

def debug_formulario_matricula(form_data):
    """
    Función de debugging para verificar datos del formulario
    """
    try:
        print(f"🔍 DEBUG: Verificando datos del formulario")
        for key, value in form_data.items():
            if hasattr(value, '__str__'):
                print(f"   {key}: {value}")
            else:
                print(f"   {key}: {type(value)}")
        
        # Verificar campos críticos
        estudiante = form_data.get('estudiante')
        curso_lectivo = form_data.get('curso_lectivo')
        nivel = form_data.get('nivel')
        especialidad = form_data.get('especialidad')
        
        if estudiante:
            print(f"   👤 Estudiante: {estudiante.identificacion} - {estudiante.nombres}")
        if curso_lectivo:
            print(f"   📅 Curso lectivo: {curso_lectivo.nombre}")
        if nivel:
            print(f"   📊 Nivel: {nivel.numero} - {nivel.nombre}")
        if especialidad:
            print(f"   🎯 Especialidad: {especialidad.especialidad.nombre}")
        
    except Exception as e:
        logger.error(f"Error en debug_formulario_matricula: {e}")
        print(f"❌ Error: {e}")

def verificar_restricciones_matricula(estudiante, curso_lectivo, nivel, especialidad=None):
    """
    Verifica todas las restricciones para una matrícula
    """
    try:
        from .models import MatriculaAcademica
        from django.core.exceptions import ValidationError
        
        print(f"🔍 DEBUG: Verificando restricciones de matrícula")
        
        # 1. Verificar si ya existe matrícula activa para este curso
        matricula_existente = MatriculaAcademica.objects.filter(
            estudiante=estudiante,
            curso_lectivo=curso_lectivo,
            estado='activo'
        ).first()
        
        if matricula_existente:
            print(f"   ⚠️  Ya existe matrícula activa: {matricula_existente}")
            return False, "Ya existe una matrícula activa para este curso lectivo"
        
        # 2. Verificar especialidad obligatoria para décimo
        if nivel.numero == 10 and not especialidad:
            print(f"   ❌ Décimo requiere especialidad obligatoria")
            return False, "La especialidad es obligatoria para décimo"
        
        # 3. Verificar especialidad para 11° y 12° si no hay previa
        if nivel.numero in [11, 12] and not especialidad:
            matricula_10 = MatriculaAcademica.objects.filter(
                estudiante=estudiante,
                nivel__numero=10,
                estado='activo'
            ).first()
            
            if not matricula_10 or not matricula_10.especialidad:
                print(f"   ❌ 11° o 12° requiere especialidad si no hay previa en décimo")
                return False, "Debe seleccionar especialidad para 11° o 12° si no existe una asignada en décimo"
        
        # 4. Verificar que la especialidad esté disponible
        if especialidad:
            especialidades_disponibles = MatriculaAcademica.get_especialidades_disponibles(
                institucion=estudiante.institucion,
                curso_lectivo=curso_lectivo
            )
            
            if especialidad not in especialidades_disponibles:
                print(f"   ❌ Especialidad no disponible: {especialidad}")
                return False, "La especialidad seleccionada no está disponible para este curso lectivo"
        
        print(f"   ✅ Todas las restricciones verificadas correctamente")
        return True, "Matrícula válida"
        
    except Exception as e:
        logger.error(f"Error en verificar_restricciones_matricula: {e}")
        print(f"❌ Error: {e}")
        return False, f"Error al verificar restricciones: {e}"