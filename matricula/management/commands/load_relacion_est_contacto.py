# matricula/management/commands/load_relacion_est_contacto.py
import os
import csv
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from matricula.models import EncargadoEstudiante, Estudiante, PersonaContacto
from catalogos.models import Parentesco

class Command(BaseCommand):
    help = "Carga la relación entre estudiantes y contactos desde el archivo relacion_est_contacto.csv"

    def handle(self, *args, **options):
        path = os.path.join(settings.BASE_DIR, 'relacion_est_contacto.csv')
        
        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"Archivo no encontrado: {path}"))
            return
        
        # Contadores
        creados = 0
        actualizados = 0
        errores = 0
        
        with transaction.atomic():
            with open(path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                for i, row in enumerate(reader, 1):
                    try:
                        # Debug: mostrar la fila actual
                        self.stdout.write(f"Procesando fila {i}: {row}")
                        
                        # Obtener el estudiante por identificación y extraer su ID interno
                        estudiante = Estudiante.objects.get(identificacion=row['estudiante_id'])
                        estudiante_id = estudiante.id
                        
                        # Obtener la persona de contacto por identificación y extraer su ID interno
                        persona_contacto = PersonaContacto.objects.get(identificacion=row['persona_contacto_id'])
                        persona_contacto_id = persona_contacto.id
                        
                        # Obtener el parentesco
                        parentesco = Parentesco.objects.get(id=row['parentesco_id'])
                        
                        # Procesar campos booleanos
                        convivencia = row['convivencia'].upper() == 'VERDADERO' if row['convivencia'] else False
                        principal = row['principal'].upper() == 'VERDADERO' if row['principal'] else False
                        
                        # Validar datos mínimos
                        if not estudiante or not persona_contacto or not parentesco:
                            self.stdout.write(f"Fila {i}: Datos insuficientes, saltando...")
                            continue
                        
                        # Crear o actualizar la relación usando los IDs internos
                        relacion, created = EncargadoEstudiante.objects.update_or_create(
                            estudiante_id=estudiante_id,
                            persona_contacto_id=persona_contacto_id,
                            parentesco=parentesco,
                            defaults={
                                'convivencia': convivencia,
                                'principal': principal,
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
                    except PersonaContacto.DoesNotExist:
                        errores += 1
                        self.stdout.write(f"Error en fila {i}: Persona de contacto con identificación {row['persona_contacto_id']} no encontrada")
                        continue
                    except Parentesco.DoesNotExist:
                        errores += 1
                        self.stdout.write(f"Error en fila {i}: Parentesco con ID {row['parentesco_id']} no encontrado")
                        continue
                    except Exception as e:
                        errores += 1
                        self.stdout.write(f"Error en fila {i}: {str(e)}")
                        self.stdout.write(f"Contenido de la fila: {row}")
                        continue
        
        self.stdout.write(self.style.SUCCESS(
            f"Relaciones cargadas: {creados} creadas, {actualizados} actualizadas, {errores} errores"
        ))
