from django.core.management.base import BaseCommand
from django.db.models import Count
from matricula.models import Estudiante, MatriculaAcademica, EncargadoEstudiante


class Command(BaseCommand):
    help = 'Limpia estudiantes duplicados dejando solo uno por identificación'

    def handle(self, *args, **options):
        self.stdout.write("Buscando estudiantes duplicados...")
        
        # Encontrar identificaciones duplicadas
        duplicados = Estudiante.objects.values('identificacion').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        total_duplicados = duplicados.count()
        self.stdout.write(f"Encontradas {total_duplicados} identificaciones duplicadas")
        
        if total_duplicados == 0:
            self.stdout.write(self.style.SUCCESS("No hay estudiantes duplicados"))
            return
        
        estudiantes_eliminados = 0
        matriculas_movidas = 0
        encargados_movidos = 0
        
        for dup in duplicados:
            identificacion = dup['identificacion']
            estudiantes_dup = Estudiante.objects.filter(identificacion=identificacion).order_by('id')
            
            # Mantener el primer estudiante, eliminar los demás
            estudiante_principal = estudiantes_dup.first()
            estudiantes_a_eliminar = estudiantes_dup.exclude(id=estudiante_principal.id)
            
            self.stdout.write(f"\nProcesando identificacion {identificacion}:")
            self.stdout.write(f"   Manteniendo: {estudiante_principal} (ID: {estudiante_principal.id})")
            
            for est_dup in estudiantes_a_eliminar:
                self.stdout.write(f"   Eliminando: {est_dup} (ID: {est_dup.id})")
                
                # Mover matrículas al estudiante principal
                matriculas = MatriculaAcademica.objects.filter(estudiante=est_dup)
                count_mat = matriculas.count()
                if count_mat > 0:
                    matriculas.update(estudiante=estudiante_principal)
                    matriculas_movidas += count_mat
                    self.stdout.write(f"      -> {count_mat} matriculas movidas")
                
                # Mover encargados al estudiante principal (evitando duplicados)
                encargados = EncargadoEstudiante.objects.filter(estudiante=est_dup)
                for encargado in encargados:
                    # Verificar si ya existe la misma relación para el estudiante principal
                    existe = EncargadoEstudiante.objects.filter(
                        estudiante=estudiante_principal,
                        persona_contacto=encargado.persona_contacto,
                        parentesco=encargado.parentesco
                    ).exists()
                    
                    if not existe:
                        encargado.estudiante = estudiante_principal
                        encargado.save()
                        encargados_movidos += 1
                        self.stdout.write(f"      -> Encargado movido")
                    else:
                        encargado.delete()
                        self.stdout.write(f"      -> Encargado duplicado eliminado")
                
                # Eliminar el estudiante duplicado
                est_dup.delete()
                estudiantes_eliminados += 1
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"Limpieza completada:"))
        self.stdout.write(f"   - Estudiantes eliminados: {estudiantes_eliminados}")
        self.stdout.write(f"   - Matriculas movidas: {matriculas_movidas}")
        self.stdout.write(f"   - Encargados movidos: {encargados_movidos}")
        self.stdout.write("="*60)

