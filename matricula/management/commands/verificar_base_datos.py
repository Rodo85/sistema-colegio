from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError
from matricula.models import Estudiante, PersonaContacto, EncargadoEstudiante, MatriculaAcademica


class Command(BaseCommand):
    help = 'Verifica y repara la base de datos de matrícula'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repair',
            action='store_true',
            help='Intenta reparar problemas encontrados',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔍 Verificando base de datos de matrícula...')
        
        # Verificar conexión a la base de datos
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                self.stdout.write(self.style.SUCCESS('✅ Conexión a la base de datos: OK'))
        except OperationalError as e:
            self.stdout.write(self.style.ERROR(f'❌ Error de conexión: {e}'))
            return

        # Verificar tablas
        tables_to_check = [
            'matricula_estudiante',
            'matricula_personacontacto', 
            'matricula_encargadoestudiante',
            'matricula_matriculaacademica'
        ]
        
        for table in tables_to_check:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    self.stdout.write(self.style.SUCCESS(f'✅ Tabla {table}: {count} registros'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error en tabla {table}: {e}'))
                if options['repair']:
                    self.stdout.write('🔧 Intentando reparar...')
                    self.repair_table(table)

        # Verificar integridad referencial
        self.check_referential_integrity()
        
        # Verificar datos inconsistentes
        self.check_data_consistency()

    def repair_table(self, table):
        """Intenta reparar una tabla problemática"""
        try:
            with connection.cursor() as cursor:
                # Verificar si la tabla existe
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    );
                """)
                exists = cursor.fetchone()[0]
                
                if not exists:
                    self.stdout.write(f'⚠️  La tabla {table} no existe. Ejecute "python manage.py migrate"')
                else:
                    self.stdout.write(f'✅ La tabla {table} existe')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ No se pudo reparar {table}: {e}'))

    def check_referential_integrity(self):
        """Verifica la integridad referencial entre tablas"""
        self.stdout.write('\n🔍 Verificando integridad referencial...')
        
        try:
            # Verificar estudiantes sin institución
            estudiantes_sin_institucion = Estudiante.objects.filter(institucion__isnull=True).count()
            if estudiantes_sin_institucion > 0:
                self.stdout.write(self.style.WARNING(f'⚠️  {estudiantes_sin_institucion} estudiantes sin institución'))
            
            # Verificar encargados con estudiantes inválidos
            encargados_invalidos = EncargadoEstudiante.objects.filter(
                estudiante__isnull=True
            ).count()
            if encargados_invalidos > 0:
                self.stdout.write(self.style.WARNING(f'⚠️  {encargados_invalidos} encargados con estudiantes inválidos'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error verificando integridad: {e}'))

    def check_data_consistency(self):
        """Verifica la consistencia de los datos"""
        self.stdout.write('\n🔍 Verificando consistencia de datos...')
        
        try:
            # Verificar estudiantes con identificaciones duplicadas por institución
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT institucion_id, identificacion, COUNT(*) 
                    FROM matricula_estudiante 
                    GROUP BY institucion_id, identificacion 
                    HAVING COUNT(*) > 1
                """)
                duplicados = cursor.fetchall()
                
                if duplicados:
                    self.stdout.write(self.style.WARNING(f'⚠️  {len(duplicados)} identificaciones duplicadas por institución'))
                else:
                    self.stdout.write(self.style.SUCCESS('✅ No hay identificaciones duplicadas'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error verificando consistencia: {e}'))

