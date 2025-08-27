from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.core.exceptions import ValidationError
from matricula.models import Estudiante, EncargadoEstudiante, MatriculaAcademica
from ingreso_clases.models import RegistroIngreso
from config_institucional.models import Clase


class Command(BaseCommand):
    help = 'Migra datos existentes para agregar campos institucion_id y mejorar seguridad multi-tenant'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🧪 MODO DRY-RUN - No se harán cambios reales'))
        
        self.stdout.write('🚀 Iniciando migración multi-tenant...')
        
        try:
            with transaction.atomic():
                # 1. Migrar RegistroIngreso
                self.migrar_registro_ingreso(dry_run)
                
                # 2. Migrar EncargadoEstudiante
                self.migrar_encargado_estudiante(dry_run)
                
                # 3. Migrar MatriculaAcademica
                self.migrar_matricula_academica(dry_run)
                
                # 4. Migrar Clase
                self.migrar_clase(dry_run)
                
                if not dry_run:
                    self.stdout.write(self.style.SUCCESS('✅ Migración completada exitosamente'))
                else:
                    self.stdout.write(self.style.SUCCESS('🧪 DRY-RUN completado - Revisar resultados'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante la migración: {str(e)}'))
            raise

    def migrar_registro_ingreso(self, dry_run):
        """Migrar registros de ingreso agregando institucion_id"""
        self.stdout.write('📝 Migrando registros de ingreso...')
        
        # Obtener registros sin institucion_id
        registros_sin_institucion = RegistroIngreso.objects.filter(
            institucion__isnull=True
        ).select_related('estudiante__institucion')
        
        count = 0
        for registro in registros_sin_institucion:
            if hasattr(registro, 'estudiante') and registro.estudiante:
                if not dry_run:
                    registro.institucion = registro.estudiante.institucion
                    registro.save()
                count += 1
        
        self.stdout.write(f"   📊 {count} registros migrados")

    def migrar_encargado_estudiante(self, dry_run):
        """Migrar encargados agregando institucion_id"""
        self.stdout.write('👥 Migrando encargados de estudiantes...')
        
        # Obtener encargados sin institucion_id
        encargados_sin_institucion = EncargadoEstudiante.objects.filter(
            institucion__isnull=True
        ).select_related('estudiante__institucion')
        
        count = 0
        for encargado in encargados_sin_institucion:
            if hasattr(encargado, 'estudiante') and encargado.estudiante:
                if not dry_run:
                    encargado.institucion = encargado.estudiante.institucion
                    encargado.save()
                count += 1
        
        self.stdout.write(f"   📊 {count} encargados migrados")

    def migrar_matricula_academica(self, dry_run):
        """Migrar matrículas agregando institucion_id"""
        self.stdout.write('🎓 Migrando matrículas académicas...')
        
        # Obtener matrículas sin institucion_id
        matriculas_sin_institucion = MatriculaAcademica.objects.filter(
            institucion__isnull=True
        ).select_related('estudiante__institucion')
        
        count = 0
        for matricula in matriculas_sin_institucion:
            if hasattr(matricula, 'estudiante') and matricula.estudiante:
                if not dry_run:
                    matricula.institucion = matricula.estudiante.institucion
                    matricula.save()
                count += 1
        
        self.stdout.write(f"   📊 {count} matrículas migradas")

    def migrar_clase(self, dry_run):
        """Migrar clases (ya tienen institucion_id, solo validar)"""
        self.stdout.write('📚 Validando clases...')
        
        # Verificar que todas las clases tengan institucion_id
        clases_sin_institucion = Clase.objects.filter(
            institucion__isnull=True
        ).count()
        
        if clases_sin_institucion > 0:
            self.stdout.write(self.style.WARNING(f"   ⚠️ {clases_sin_institucion} clases sin institucion_id"))
        else:
            self.stdout.write("   ✅ Todas las clases tienen institucion_id")

    def verificar_integridad(self):
        """Verificar la integridad de los datos después de la migración"""
        self.stdout.write('🔍 Verificando integridad de datos...')
        
        # Verificar que no queden registros sin institucion_id
        sin_institucion = {
            'RegistroIngreso': RegistroIngreso.objects.filter(institucion__isnull=True).count(),
            'EncargadoEstudiante': EncargadoEstudiante.objects.filter(institucion__isnull=True).count(),
            'MatriculaAcademica': MatriculaAcademica.objects.filter(institucion__isnull=True).count(),
        }
        
        for modelo, count in sin_institucion.items():
            if count > 0:
                self.stdout.write(self.style.WARNING(f"   ⚠️ {modelo}: {count} registros sin institucion_id"))
            else:
                self.stdout.write(f"   ✅ {modelo}: Todos los registros tienen institucion_id")












