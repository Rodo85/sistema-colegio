from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.exceptions import ValidationError
from matricula.models import Estudiante, EncargadoEstudiante, MatriculaAcademica
from ingreso_clases.models import RegistroIngreso
from config_institucional.models import Clase, SubgrupoCursoLectivo, SeccionCursoLectivo


class Command(BaseCommand):
    help = 'Valida la integridad multi-tenant del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Intentar corregir problemas encontrados',
        )

    def handle(self, *args, **options):
        fix = options['fix']
        
        if fix:
            self.stdout.write(self.style.WARNING('🔧 MODO CORRECCIÓN - Intentando corregir problemas'))
        
        self.stdout.write('🔍 Iniciando validación multi-tenant...')
        
        try:
            with transaction.atomic():
                # 1. Validar registros de ingreso
                self.validar_registro_ingreso(fix)
                
                # 2. Validar encargados
                self.validar_encargados(fix)
                
                # 3. Validar matrículas
                self.validar_matriculas(fix)
                
                # 4. Validar clases
                self.validar_clases(fix)
                
                # 5. Validar configuraciones institucionales
                self.validar_configuraciones_institucionales(fix)
                
                self.stdout.write(self.style.SUCCESS('✅ Validación completada'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante la validación: {str(e)}'))
            raise

    def validar_registro_ingreso(self, fix):
        """Validar que todos los registros de ingreso tengan institucion_id"""
        self.stdout.write('📝 Validando registros de ingreso...')
        
        registros_sin_institucion = RegistroIngreso.objects.filter(
            institucion__isnull=True
        )
        
        if registros_sin_institucion.exists():
            self.stdout.write(self.style.WARNING(f"   ⚠️ {registros_sin_institucion.count()} registros sin institucion_id"))
            
            if fix:
                # Intentar asignar institución basándose en la identificación
                for registro in registros_sin_institucion:
                    try:
                        estudiante = Estudiante.objects.get(identificacion=registro.identificacion)
                        registro.institucion = estudiante.institucion
                        registro.save()
                        self.stdout.write(f"      ✅ Corregido registro {registro.id}")
                    except Estudiante.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f"      ❌ No se pudo corregir registro {registro.id} - estudiante no encontrado"))
        else:
            self.stdout.write("   ✅ Todos los registros tienen institucion_id")

    def validar_encargados(self, fix):
        """Validar que todos los encargados tengan institucion_id"""
        self.stdout.write('👥 Validando encargados...')
        
        encargados_sin_institucion = EncargadoEstudiante.objects.filter(
            institucion__isnull=True
        )
        
        if encargados_sin_institucion.exists():
            self.stdout.write(self.style.WARNING(f"   ⚠️ {encargados_sin_institucion.count()} encargados sin institucion_id"))
            
            if fix:
                for encargado in encargados_sin_institucion:
                    try:
                        encargado.institucion = encargado.estudiante.institucion
                        encargado.save()
                        self.stdout.write(f"      ✅ Corregido encargado {encargado.id}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"      ❌ No se pudo corregir encargado {encargado.id}: {str(e)}"))
        else:
            self.stdout.write("   ✅ Todos los encargados tienen institucion_id")

    def validar_matriculas(self, fix):
        """Validar que todas las matrículas tengan institucion_id"""
        self.stdout.write('🎓 Validando matrículas...')
        
        matriculas_sin_institucion = MatriculaAcademica.objects.filter(
            institucion__isnull=True
        )
        
        if matriculas_sin_institucion.exists():
            self.stdout.write(self.style.WARNING(f"   ⚠️ {matriculas_sin_institucion.count()} matrículas sin institucion_id"))
            
            if fix:
                for matricula in matriculas_sin_institucion:
                    try:
                        matricula.institucion = matricula.estudiante.institucion
                        matricula.save()
                        self.stdout.write(f"      ✅ Corregida matrícula {matricula.id}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"      ❌ No se pudo corregir matrícula {matricula.id}: {str(e)}"))
        else:
            self.stdout.write("   ✅ Todas las matrículas tienen institucion_id")

    def validar_clases(self, fix):
        """Validar que todas las clases tengan institucion_id y curso_lectivo_id"""
        self.stdout.write('📚 Validando clases...')
        
        clases_sin_institucion = Clase.objects.filter(institucion__isnull=True)
        clases_sin_curso_lectivo = Clase.objects.filter(curso_lectivo__isnull=True)
        
        if clases_sin_institucion.exists():
            self.stdout.write(self.style.WARNING(f"   ⚠️ {clases_sin_institucion.count()} clases sin institucion_id"))
        
        if clases_sin_curso_lectivo.exists():
            self.stdout.write(self.style.WARNING(f"   ⚠️ {clases_sin_curso_lectivo.count()} clases sin curso_lectivo_id"))
        
        if not clases_sin_institucion.exists() and not clases_sin_curso_lectivo.exists():
            self.stdout.write("   ✅ Todas las clases tienen institucion_id y curso_lectivo_id")

    def validar_configuraciones_institucionales(self, fix):
        """Validar que las configuraciones institucionales estén correctas"""
        self.stdout.write('⚙️ Validando configuraciones institucionales...')
        
        # Verificar que no haya configuraciones duplicadas
        from django.db.models import Count
        
        # Subgrupos duplicados
        subgrupos_duplicados = SubgrupoCursoLectivo.objects.values(
            'institucion', 'curso_lectivo', 'subgrupo'
        ).annotate(count=Count('id')).filter(count__gt=1)
        
        if subgrupos_duplicados.exists():
            self.stdout.write(self.style.WARNING(f"   ⚠️ {subgrupos_duplicados.count()} configuraciones de subgrupo duplicadas"))
        
        # Secciones duplicadas
        secciones_duplicadas = SeccionCursoLectivo.objects.values(
            'institucion', 'curso_lectivo', 'seccion'
        ).annotate(count=Count('id')).filter(count__gt=1)
        
        if secciones_duplicadas.exists():
            self.stdout.write(self.style.WARNING(f"   ⚠️ {secciones_duplicadas.count()} configuraciones de sección duplicadas"))
        
        if not subgrupos_duplicados.exists() and not secciones_duplicadas.exists():
            self.stdout.write("   ✅ No hay configuraciones duplicadas")








































