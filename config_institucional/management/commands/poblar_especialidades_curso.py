from django.core.management.base import BaseCommand
from django.db import transaction
from config_institucional.models import EspecialidadCursoLectivo
from catalogos.models import CursoLectivo
from catalogos.models import Especialidad
from core.models import Institucion


class Command(BaseCommand):
    help = 'Pobla la tabla EspecialidadCursoLectivo con especialidades para cada colegio y curso lectivo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--institucion',
            type=str,
            help='Nombre de la institución específica (opcional)'
        )
        parser.add_argument(
            '--curso-lectivo',
            type=int,
            help='Año del curso lectivo específico (opcional)'
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Iniciando población de especialidades por curso lectivo...')
        
        try:
            # Verificar datos existentes primero
            instituciones_count = Institucion.objects.count()
            cursos_count = CursoLectivo.objects.count()
            especialidades_count = Especialidad.objects.count()
            
            self.stdout.write(f'📊 DATOS EXISTENTES:')
            self.stdout.write(f'   - Instituciones: {instituciones_count}')
            self.stdout.write(f'   - Cursos lectivos: {cursos_count}')
            self.stdout.write(f'   - Especialidades: {especialidades_count}')
            
            if instituciones_count == 0 or cursos_count == 0 or especialidades_count == 0:
                self.stdout.write(self.style.WARNING('⚠️ Faltan datos básicos. Asegúrate de tener instituciones, cursos lectivos y especialidades.'))
                return
            
            with transaction.atomic():
                # Obtener instituciones
                instituciones = Institucion.objects.all()
                if options['institucion']:
                    instituciones = instituciones.filter(nombre__icontains=options['institucion'])
                
                # Obtener cursos lectivos
                cursos_lectivos = CursoLectivo.objects.all()
                if options['curso_lectivo']:
                    cursos_lectivos = cursos_lectivos.filter(anio=options['curso_lectivo'])
                
                # Obtener todas las especialidades
                especialidades = Especialidad.objects.all()
                
                contador_creados = 0
                contador_existentes = 0
                
                for institucion in instituciones:
                    self.stdout.write(f'📚 Procesando institución: {institucion.nombre}')
                    
                    cursos_institucion = cursos_lectivos.filter(institucion=institucion)
                    if not cursos_institucion.exists():
                        self.stdout.write(f'   ⚠️ No hay cursos lectivos para esta institución')
                        continue
                    
                    for curso_lectivo in cursos_institucion:
                        self.stdout.write(f'   📅 Curso lectivo: {curso_lectivo.nombre}')
                        
                        for especialidad in especialidades:
                            # Crear o actualizar la configuración
                            obj, created = EspecialidadCursoLectivo.objects.get_or_create(
                                institucion=institucion,
                                curso_lectivo=curso_lectivo,
                                especialidad=especialidad,
                                defaults={
                                    'activa': True,  # Por defecto activa
                                }
                            )
                            
                            if created:
                                contador_creados += 1
                                if contador_creados <= 5:  # Mostrar solo los primeros 5
                                    self.stdout.write(f'      ✅ Creada: {especialidad.nombre}')
                            else:
                                contador_existentes += 1
                
                self.stdout.write('')
                self.stdout.write('📊 RESUMEN:')
                self.stdout.write(f'   🆕 Especialidades creadas: {contador_creados}')
                self.stdout.write(f'   🔄 Especialidades existentes: {contador_existentes}')
                self.stdout.write(f'   📈 Total procesadas: {contador_creados + contador_existentes}')
                self.stdout.write('')
                
                if contador_creados > 0:
                    self.stdout.write('✅ Población completada exitosamente!')
                    self.stdout.write('🎯 Ahora cada institución puede configurar qué especialidades usar en cada curso lectivo.')
                else:
                    self.stdout.write('ℹ️ No se crearon registros nuevos (ya existían).')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante la población: {str(e)}'))
            raise
