from django.core.management.base import BaseCommand
from django.db import transaction
from matricula.models import Estudiante, PersonaContacto, EncargadoEstudiante
from catalogos.models import Parentesco
import csv


class Command(BaseCommand):
    help = 'Importar relaciones entre estudiantes y encargados desde relacion_est_contacto.csv'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='relacion_est_contacto.csv',
            help='Ruta del archivo CSV con las relaciones'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué se haría, sin guardar cambios'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  MODO DRY-RUN: No se guardarán cambios'))
        
        self.stdout.write(f'📂 Leyendo archivo: {file_path}')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                
                relaciones_creadas = 0
                relaciones_existentes = 0
                errores = 0
                
                for i, row in enumerate(reader, start=2):
                    try:
                        # Leer datos del CSV
                        estudiante_identificacion = row['estudiante_id'].strip()
                        contacto_identificacion = row['persona_contacto_id'].strip()
                        parentesco_id = int(row['parentesco_id'])
                        convivencia = row['convivencia'].strip().upper() == 'VERDADERO'
                        principal = row['principal'].strip().upper() == 'VERDADERO'
                        
                        # Buscar estudiante por identificación
                        try:
                            estudiante = Estudiante.objects.get(identificacion=estudiante_identificacion)
                        except Estudiante.DoesNotExist:
                            self.stdout.write(
                                self.style.ERROR(f'  ❌ Línea {i}: Estudiante con identificación {estudiante_identificacion} no encontrado')
                            )
                            errores += 1
                            continue
                        except Estudiante.MultipleObjectsReturned:
                            self.stdout.write(
                                self.style.ERROR(f'  ❌ Línea {i}: Múltiples estudiantes con identificación {estudiante_identificacion}')
                            )
                            errores += 1
                            continue
                        
                        # Buscar persona de contacto por identificación
                        try:
                            persona_contacto = PersonaContacto.objects.get(identificacion=contacto_identificacion)
                        except PersonaContacto.DoesNotExist:
                            self.stdout.write(
                                self.style.ERROR(f'  ❌ Línea {i}: Persona de contacto con identificación {contacto_identificacion} no encontrada')
                            )
                            errores += 1
                            continue
                        except PersonaContacto.MultipleObjectsReturned:
                            # Si hay múltiples, intentar filtrar por institución del estudiante
                            institucion_estudiante = estudiante.get_institucion_activa()
                            if institucion_estudiante:
                                try:
                                    persona_contacto = PersonaContacto.objects.get(
                                        identificacion=contacto_identificacion,
                                        institucion=institucion_estudiante
                                    )
                                except PersonaContacto.DoesNotExist:
                                    self.stdout.write(
                                        self.style.ERROR(f'  ❌ Línea {i}: Persona de contacto {contacto_identificacion} no encontrada en institución del estudiante')
                                    )
                                    errores += 1
                                    continue
                            else:
                                self.stdout.write(
                                    self.style.ERROR(f'  ❌ Línea {i}: Múltiples personas de contacto con identificación {contacto_identificacion} y estudiante sin institución activa')
                                )
                                errores += 1
                                continue
                        
                        # Buscar parentesco
                        try:
                            parentesco = Parentesco.objects.get(id=parentesco_id)
                        except Parentesco.DoesNotExist:
                            self.stdout.write(
                                self.style.ERROR(f'  ❌ Línea {i}: Parentesco con ID {parentesco_id} no encontrado')
                            )
                            errores += 1
                            continue
                        
                        # Verificar si ya existe la relación
                        if EncargadoEstudiante.objects.filter(
                            estudiante=estudiante,
                            persona_contacto=persona_contacto,
                            parentesco=parentesco
                        ).exists():
                            relaciones_existentes += 1
                            if i <= 10:  # Solo mostrar los primeros 10
                                self.stdout.write(
                                    self.style.WARNING(f'  ⏭️  Línea {i}: Relación ya existe')
                                )
                            continue
                        
                        # Crear la relación
                        if not dry_run:
                            with transaction.atomic():
                                EncargadoEstudiante.objects.create(
                                    estudiante=estudiante,
                                    persona_contacto=persona_contacto,
                                    parentesco=parentesco,
                                    convivencia=convivencia,
                                    principal=principal
                                )
                        
                        relaciones_creadas += 1
                        if relaciones_creadas <= 10:  # Mostrar los primeros 10
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✅ Línea {i}: {estudiante.nombres} {estudiante.primer_apellido} ← {persona_contacto.nombres} {persona_contacto.primer_apellido} ({parentesco.descripcion})'
                                )
                            )
                        elif relaciones_creadas % 50 == 0:  # Mostrar progreso cada 50
                            self.stdout.write(f'  📊 {relaciones_creadas} relaciones procesadas...')
                    
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  ❌ Línea {i}: Error inesperado: {str(e)}')
                        )
                        errores += 1
                
                # Resumen
                self.stdout.write('\n' + '='*70)
                self.stdout.write('📊 RESUMEN DE IMPORTACIÓN:')
                self.stdout.write('='*70)
                self.stdout.write(f'  ✅ Relaciones creadas:    {relaciones_creadas}')
                self.stdout.write(f'  ⏭️  Relaciones existentes: {relaciones_existentes}')
                self.stdout.write(f'  ❌ Errores:               {errores}')
                self.stdout.write(f'  📊 Total procesadas:      {relaciones_creadas + relaciones_existentes + errores}')
                
                if dry_run:
                    self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: No se guardaron cambios. Ejecuta sin --dry-run para aplicar.'))
                else:
                    self.stdout.write(self.style.SUCCESS('\n✅ Importación completada'))
        
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ Archivo no encontrado: {file_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error al procesar archivo: {str(e)}'))








