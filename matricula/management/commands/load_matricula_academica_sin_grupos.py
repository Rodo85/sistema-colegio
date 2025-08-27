import os
import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from matricula.models import MatriculaAcademica, Estudiante
from catalogos.models import Nivel, CursoLectivo
from config_institucional.models import EspecialidadCursoLectivo


class Command(BaseCommand):
    help = (
        "Carga matrículas académicas SIN secciones/subgrupos. "
        "Por defecto usa matricula_academica2025.csv e ignora las dos últimas columnas."
    )

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, help='Ruta al CSV. Por defecto matricula_academica2025.csv en BASE_DIR')

    def handle(self, *args, **options):
        # Por defecto usamos el archivo completo y simplemente ignoramos seccion_id/subgrupo_id
        path = options.get('path') or os.path.join(settings.BASE_DIR, 'matricula_academica2025.csv')

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
                        # Estudiante por identificación externa
                        estudiante = Estudiante.objects.get(identificacion=row['estudiante_id'])

                        nivel = Nivel.objects.get(id=row['nivel_id'])
                        curso_lectivo = CursoLectivo.objects.get(id=row['curso_lectivo_id'])

                        especialidad = None
                        if row.get('especialidad_id') and row['especialidad_id'].strip():
                            especialidad = EspecialidadCursoLectivo.objects.get(id=row['especialidad_id'])

                        # Fecha
                        fecha_asignacion = None
                        if row.get('fecha_asignacion') and row['fecha_asignacion'].strip():
                            try:
                                fecha_asignacion = datetime.strptime(row['fecha_asignacion'], '%d/%m/%Y').date()
                            except ValueError:
                                self.stdout.write(f"Fila {i}: Formato de fecha inválido: {row['fecha_asignacion']}")
                                continue

                        estado = (row.get('estado') or 'activo').strip().lower()

                        # Crear/actualizar sin seccion/subgrupo
                        matricula, created = MatriculaAcademica.objects.update_or_create(
                            estudiante=estudiante,
                            nivel=nivel,
                            curso_lectivo=curso_lectivo,
                            defaults={
                                'fecha_asignacion': fecha_asignacion,
                                'estado': estado,
                                'especialidad': especialidad,
                                'seccion': None,
                                'subgrupo': None,
                            }
                        )

                        if created:
                            creados += 1
                        else:
                            actualizados += 1

                    except Estudiante.DoesNotExist:
                        errores += 1
                        self.stdout.write(f"Error fila {i}: Estudiante {row['estudiante_id']} no encontrado")
                    except Nivel.DoesNotExist:
                        errores += 1
                        self.stdout.write(f"Error fila {i}: Nivel {row['nivel_id']} no encontrado")
                    except CursoLectivo.DoesNotExist:
                        errores += 1
                        self.stdout.write(f"Error fila {i}: Curso lectivo {row['curso_lectivo_id']} no encontrado")
                    except EspecialidadCursoLectivo.DoesNotExist:
                        errores += 1
                        self.stdout.write(f"Error fila {i}: EspecialidadCursoLectivo {row['especialidad_id']} no encontrada")
                    except Exception as e:
                        errores += 1
                        self.stdout.write(f"Error fila {i}: {e}")
                        self.stdout.write(f"Fila: {row}")

        self.stdout.write(self.style.SUCCESS(
            f"Carga sin grupos finalizada: {creados} creadas, {actualizados} actualizadas, {errores} errores"
        ))


