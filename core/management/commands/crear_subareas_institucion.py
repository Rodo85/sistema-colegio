from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Institucion
from catalogos.models import SubArea, SubAreaInstitucion


class Command(BaseCommand):
    help = 'Crea configuraciones de SubAreaInstitucion para todas las instituciones existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--institucion',
            type=str,
            help='ID o nombre de una institución específica (opcional)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se haría sin ejecutar cambios'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        institucion_specifica = options['institucion']

        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se harán cambios'))

        # Obtener instituciones
        if institucion_specifica:
            try:
                # Intentar por ID primero
                if institucion_specifica.isdigit():
                    instituciones = Institucion.objects.filter(id=institucion_specifica)
                else:
                    instituciones = Institucion.objects.filter(nombre__icontains=institucion_specifica)
                
                if not instituciones.exists():
                    self.stdout.write(
                        self.style.ERROR(f'No se encontró institución con: {institucion_specifica}')
                    )
                    return
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error al buscar institución: {e}')
                )
                return
        else:
            instituciones = Institucion.objects.all()

        # Obtener todas las subáreas
        subareas = SubArea.objects.all()

        self.stdout.write(f'Procesando {instituciones.count()} instituciones...')
        self.stdout.write(f'Total de subáreas: {subareas.count()}')

        total_creadas = 0
        total_existentes = 0

        for institucion in instituciones:
            self.stdout.write(f'\nProcesando institución: {institucion.nombre}')
            
            for subarea in subareas:
                # Verificar si ya existe
                if SubAreaInstitucion.objects.filter(
                    institucion=institucion,
                    subarea=subarea
                ).exists():
                    total_existentes += 1
                    continue

                if not dry_run:
                    try:
                        with transaction.atomic():
                            SubAreaInstitucion.objects.create(
                                institucion=institucion,
                                subarea=subarea,
                                activa=True
                            )
                        total_creadas += 1
                        self.stdout.write(f'  ✓ Creada: {subarea.nombre}')
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Error creando {subarea.nombre}: {e}')
                        )
                else:
                    total_creadas += 1
                    self.stdout.write(f'  ✓ Se crearía: {subarea.nombre}')

        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'RESUMEN:')
        self.stdout.write(f'  • Configuraciones existentes: {total_existentes}')
        self.stdout.write(f'  • Configuraciones a crear: {total_creadas}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nMODO DRY-RUN: Ejecuta sin --dry-run para aplicar cambios')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n¡Completado! Se crearon {total_creadas} configuraciones')
            )