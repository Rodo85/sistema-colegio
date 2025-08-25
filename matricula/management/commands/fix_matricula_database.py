from django.core.management.base import BaseCommand
from django.db import connection
from django.core.exceptions import ValidationError


class Command(BaseCommand):
    help = 'Verifica y corrige problemas en la base de datos de matrícula'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Aplicar correcciones automáticamente',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada',
        )

    def handle(self, *args, **options):
        fix = options['fix']
        verbose = options['verbose']
        
        self.stdout.write(self.style.SUCCESS('🔍 Verificando base de datos de matrícula...'))
        
        with connection.cursor() as cursor:
            # Verificar estructura de la tabla
            self.check_table_structure(cursor, verbose)
            
            # Verificar constraints
            self.check_constraints(cursor, verbose)
            
            # Verificar datos
            self.check_data_integrity(cursor, verbose)
            
            # Aplicar correcciones si se solicita
            if fix:
                self.apply_fixes(cursor, verbose)
        
        self.stdout.write(self.style.SUCCESS('✅ Verificación completada'))

    def check_table_structure(self, cursor, verbose):
        """Verifica la estructura de la tabla"""
        self.stdout.write('\n📋 Verificando estructura de la tabla...')
        
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'matricula_matriculaacademica'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        
        if verbose:
            self.stdout.write(f"{'Columna':<20} {'Tipo':<15} {'Nullable':<8} {'Default':<15}")
            self.stdout.write("-" * 60)
            for col in columns:
                column_name, data_type, is_nullable, column_default = col
                self.stdout.write(f"{column_name:<20} {data_type:<15} {is_nullable:<8} {str(column_default):<15}")
        
        # Verificar si existe el campo institución incorrecto
        has_institucion = any(col[0] == 'institucion_id' for col in columns)
        
        if has_institucion:
            self.stdout.write(
                self.style.WARNING('⚠️  PROBLEMA: Campo institución_id encontrado en la tabla')
            )
            if verbose:
                self.stdout.write('   Este campo no debería existir según el modelo actual')
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ Estructura de tabla correcta')
            )
        
        return has_institucion

    def check_constraints(self, cursor, verbose):
        """Verifica los constraints de la tabla"""
        self.stdout.write('\n🔒 Verificando constraints...')
        
        cursor.execute("""
            SELECT conname, contype, pg_get_constraintdef(oid) as definition
            FROM pg_constraint 
            WHERE conrelid = 'matricula_matriculaacademica'::regclass;
        """)
        
        constraints = cursor.fetchall()
        
        if verbose:
            for con in constraints:
                self.stdout.write(f"  - {con[0]} ({con[1]}): {con[2]}")
        
        # Verificar constraint de matrícula única por año
        has_unique_constraint = any('uniq_matricula_activa_por_anio' in con[0] for con in constraints)
        
        if has_unique_constraint:
            self.stdout.write(
                self.style.SUCCESS('✅ Constraint de matrícula única por año encontrado')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️  Falta constraint de matrícula única por año')
            )
        
        return has_unique_constraint

    def check_data_integrity(self, cursor, verbose):
        """Verifica la integridad de los datos"""
        self.stdout.write('\n📊 Verificando integridad de datos...')
        
        # Contar total de registros
        cursor.execute("SELECT COUNT(*) FROM matricula_matriculaacademica;")
        total_count = cursor.fetchone()[0]
        self.stdout.write(f"  Total de registros: {total_count}")
        
        if total_count > 0:
            # Verificar registros con problemas
            cursor.execute("""
                SELECT m.id, m.estudiante_id, e.identificacion, e.nombres, e.institucion_id
                FROM matricula_matriculaacademica m
                JOIN matricula_estudiante e ON m.estudiante_id = e.id
                WHERE e.institucion_id IS NULL;
            """)
            
            problematic_records = cursor.fetchall()
            
            if problematic_records:
                self.stdout.write(
                    self.style.ERROR(f'❌ {len(problematic_records)} registros con estudiantes sin institución')
                )
                if verbose:
                    for record in problematic_records:
                        self.stdout.write(f"    - Matrícula ID: {record[0]}, Estudiante: {record[2]} {record[3]}")
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ Todos los estudiantes tienen institución asignada')
                )
        
        return total_count

    def apply_fixes(self, cursor, verbose):
        """Aplica correcciones automáticas"""
        self.stdout.write('\n🔧 Aplicando correcciones...')
        
        try:
            # 1. Remover campo institución si existe
            cursor.execute("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'matricula_matriculaacademica' 
                        AND column_name = 'institucion_id'
                    ) THEN
                        ALTER TABLE matricula_matriculaacademica DROP COLUMN IF EXISTS institucion_id;
                        RAISE NOTICE 'Columna institución removida';
                    END IF;
                END $$;
            """)
            
            # 2. Agregar constraint de matrícula única si no existe
            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'uniq_matricula_activa_por_anio'
                    ) THEN
                        ALTER TABLE matricula_matriculaacademica 
                        ADD CONSTRAINT uniq_matricula_activa_por_anio 
                        UNIQUE (estudiante_id, curso_lectivo_id) 
                        WHERE estado = 'activo';
                        RAISE NOTICE 'Constraint de matrícula única agregado';
                    END IF;
                END $$;
            """)
            
            self.stdout.write(
                self.style.SUCCESS('✅ Correcciones aplicadas exitosamente')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al aplicar correcciones: {e}')
            )
            raise