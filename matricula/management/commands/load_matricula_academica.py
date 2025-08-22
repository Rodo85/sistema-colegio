import os
import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from matricula.models import MatriculaAcademica, Estudiante
from catalogos.models import Nivel, Seccion, Subgrupo, CursoLectivo
from config_institucional.models import EspecialidadCursoLectivo

class Command(BaseCommand):
    help = "Carga matrículas académicas desde el archivo matricula_academica2025.csv"

    def handle(self, *args, **options):
        path = os.path.join(settings.BASE_DIR, 'matricula_academica2025.csv')
        
        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"Archivo no encontrado: {path}"))
            return
        
        creados = 0
        actualizados = 0
        errores = 0
        
        with transaction.atomic():
            with open(path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                for i, row in enumerate(reader, 1):
                    try:
                        self.stdout.write(f"Procesando fila {i}: {row}")
                        
                        # Obtener el estudiante por identificación y extraer su ID interno
                        estudiante = Estudiante.objects.get(identificacion=row['estudiante_id'])
                        estudiante_id = estudiante.id
                        
                        # Obtener las referencias a los modelos relacionados
                        nivel = Nivel.objects.get(id=row['nivel_id'])
                        curso_lectivo = CursoLectivo.objects.get(id=row['curso_lectivo_id'])
                        
                        # Campos opcionales
                        seccion = None
                        if row['seccion_id'] and row['seccion_id'].strip():
                            seccion = Seccion.objects.get(id=row['seccion_id'])
                        
                        subgrupo = None
                        if row['subgrupo_id'] and row['subgrupo_id'].strip():
                            subgrupo = Subgrupo.objects.get(id=row['subgrupo_id'])
                        
                        especialidad = None
                        if row['especialidad_id'] and row['especialidad_id'].strip():
                            # Buscar la especialidad en EspecialidadCursoLectivo por su ID
                            especialidad = EspecialidadCursoLectivo.objects.get(id=row['especialidad_id'])
                        
                        # Procesar fecha de asignación
                        fecha_asignacion = None
                        if row['fecha_asignacion'] and row['fecha_asignacion'].strip():
                            try:
                                fecha_asignacion = datetime.strptime(row['fecha_asignacion'], '%d/%m/%Y').date()
                            except ValueError:
                                self.stdout.write(f"Fila {i}: Formato de fecha inválido: {row['fecha_asignacion']}")
                                continue
                        
                        # Procesar estado
                        estado = row['estado'].strip().lower() if row['estado'] else 'activo'
                        
                        # Validar que los datos requeridos estén presentes
                        if not estudiante or not nivel or not curso_lectivo:
                            self.stdout.write(f"Fila {i}: Datos insuficientes, saltando...")
                            continue
                        
                        # Crear o actualizar la matrícula académica usando el ID interno del estudiante
                        matricula, created = MatriculaAcademica.objects.update_or_create(
                            estudiante_id=estudiante_id,
                            nivel=nivel,
                            seccion=seccion,
                            subgrupo=subgrupo,
                            curso_lectivo=curso_lectivo,
                            defaults={
                                'fecha_asignacion': fecha_asignacion,
                                'estado': estado,
                                'especialidad': especialidad,
                            }
                        )
                        
                        if created:
                            creados += 1
                        else:
                            actualizados += 1
                            
                    except Estudiante.DoesNotExist:
                        errores += 1
                        self.stdout.write(f"Error en fila {i}: Estudiante con identificación {row['estudiante_id']} no encontrado")
                        continue
                    except Nivel.DoesNotExist:
                        errores += 1
                        self.stdout.write(f"Error en fila {i}: Nivel con ID {row['nivel_id']} no encontrado")
                        continue
                    except CursoLectivo.DoesNotExist:
                        errores += 1
                        self.stdout.write(f"Error en fila {i}: Curso lectivo con ID {row['curso_lectivo_id']} no encontrado")
                        continue
                    except Seccion.DoesNotExist:
                        errores += 1
                        self.stdout.write(f"Error en fila {i}: Sección con ID {row['seccion_id']} no encontrada")
                        continue
                    except Subgrupo.DoesNotExist:
                        errores += 1
                        self.stdout.write(f"Error en fila {i}: Subgrupo con ID {row['subgrupo_id']} no encontrado")
                        continue
                    except EspecialidadCursoLectivo.DoesNotExist:
                        errores += 1
                        self.stdout.write(f"Error en fila {i}: Especialidad del curso lectivo con ID {row['especialidad_id']} no encontrada")
                        continue
                    except Exception as e:
                        errores += 1
                        self.stdout.write(f"Error en fila {i}: {str(e)}")
                        self.stdout.write(f"Contenido de la fila: {row}")
                        continue
        
        self.stdout.write(self.style.SUCCESS(
            f"Matrículas académicas cargadas: {creados} creadas, {actualizados} actualizadas, {errores} errores"
        ))
