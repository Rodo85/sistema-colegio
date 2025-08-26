from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Institucion
from catalogos.models import CursoLectivo, Especialidad, Seccion, Subgrupo
from config_institucional.models import (
    EspecialidadCursoLectivo, 
    SeccionCursoLectivo, 
    SubgrupoCursoLectivo
)


class Command(BaseCommand):
    help = 'Crea configuraciones de curso lectivo para todas las instituciones existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--institucion',
            type=str,
            help='ID o nombre de una institución específica (opcional)'
        )
        parser.add_argument(
            '--curso-lectivo',
            type=str,
            help='ID o año del curso lectivo específico (opcional)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se haría sin ejecutar cambios'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        institucion_specifica = options['institucion']
        curso_lectivo_specifico = options['curso_lectivo']

        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se harán cambios'))

        # Obtener instituciones
        if institucion_specifica:
            try:
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

        # Obtener cursos lectivos
        if curso_lectivo_specifico:
            try:
                if curso_lectivo_specifico.isdigit():
                    cursos_lectivos = CursoLectivo.objects.filter(anio=curso_lectivo_specifico)
                else:
                    cursos_lectivos = CursoLectivo.objects.filter(nombre__icontains=curso_lectivo_specifico)
                
                if not cursos_lectivos.exists():
                    self.stdout.write(
                        self.style.ERROR(f'No se encontró curso lectivo con: {curso_lectivo_specifico}')
                    )
                    return
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error al buscar curso lectivo: {e}')
                )
                return
        else:
            cursos_lectivos = CursoLectivo.objects.filter(activo=True)

        # Obtener catálogos
        especialidades = Especialidad.objects.all()
        secciones = Seccion.objects.all()
        subgrupos = Subgrupo.objects.all()

        self.stdout.write(f'Procesando {instituciones.count()} instituciones...')
        self.stdout.write(f'Total de cursos lectivos: {cursos_lectivos.count()}')
        self.stdout.write(f'Total de especialidades: {especialidades.count()}')
        self.stdout.write(f'Total de secciones: {secciones.count()}')
        self.stdout.write(f'Total de subgrupos: {subgrupos.count()}')

        total_creadas = 0
        total_existentes = 0

        for institucion in instituciones:
            self.stdout.write(f'\nProcesando institución: {institucion.nombre}')
            
            for curso_lectivo in cursos_lectivos:
                self.stdout.write(f'  Curso lectivo: {curso_lectivo.nombre}')
                
                # Crear configuraciones de especialidades
                for especialidad in especialidades:
                    if EspecialidadCursoLectivo.objects.filter(
                        institucion=institucion,
                        curso_lectivo=curso_lectivo,
                        especialidad=especialidad
                    ).exists():
                        total_existentes += 1
                        continue

                    if not dry_run:
                        try:
                            with transaction.atomic():
                                EspecialidadCursoLectivo.objects.create(
                                    institucion=institucion,
                                    curso_lectivo=curso_lectivo,
                                    especialidad=especialidad,
                                    activa=True
                                )
                            total_creadas += 1
                            self.stdout.write(f'    ✓ Especialidad: {especialidad.nombre}')
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'    ✗ Error especialidad {especialidad.nombre}: {e}')
                            )
                    else:
                        total_creadas += 1
                        self.stdout.write(f'    ✓ Se crearía especialidad: {especialidad.nombre}')

                # Crear configuraciones de secciones
                for seccion in secciones:
                    if SeccionCursoLectivo.objects.filter(
                        institucion=institucion,
                        curso_lectivo=curso_lectivo,
                        seccion=seccion
                    ).exists():
                        total_existentes += 1
                        continue

                    if not dry_run:
                        try:
                            with transaction.atomic():
                                SeccionCursoLectivo.objects.create(
                                    institucion=institucion,
                                    curso_lectivo=curso_lectivo,
                                    seccion=seccion,
                                    activa=True
                                )
                            total_creadas += 1
                            self.stdout.write(f'    ✓ Sección: {seccion}')
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'    ✗ Error sección {seccion}: {e}')
                            )
                    else:
                        total_creadas += 1
                        self.stdout.write(f'    ✓ Se crearía sección: {seccion}')

                # Crear configuraciones de subgrupos
                for subgrupo in subgrupos:
                    if SubgrupoCursoLectivo.objects.filter(
                        institucion=institucion,
                        curso_lectivo=curso_lectivo,
                        subgrupo=subgrupo
                    ).exists():
                        total_existentes += 1
                        continue

                    if not dry_run:
                        try:
                            with transaction.atomic():
                                SubgrupoCursoLectivo.objects.create(
                                    institucion=institucion,
                                    curso_lectivo=curso_lectivo,
                                    subgrupo=subgrupo,
                                    activa=True
                                )
                            total_creadas += 1
                            self.stdout.write(f'    ✓ Subgrupo: {subgrupo}')
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'    ✗ Error subgrupo {subgrupo}: {e}')
                            )
                    else:
                        total_creadas += 1
                        self.stdout.write(f'    ✓ Se crearía subgrupo: {subgrupo}')

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