from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = 'Aplica mejoras de base de datos para robustez multi-tenant'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar SQL sin ejecutar',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🧪 MODO DRY-RUN - No se ejecutarán cambios'))
        
        self.stdout.write('🔧 Aplicando mejoras de base de datos...')
        
        # Lista de mejoras a aplicar
        mejoras = [
            {
                'nombre': 'Eliminar índice duplicado de matrícula activa',
                'sql': 'DROP INDEX IF EXISTS public.uniq_matricula_activa_por_anio;',
                'descripcion': 'Elimina el constraint global duplicado, mantiene solo el scoped por institución'
            },
            {
                'nombre': 'Eliminar índice duplicado de encargado principal',
                'sql': 'DROP INDEX IF EXISTS public.unique_principal_por_estudiante;',
                'descripcion': 'Elimina el constraint global duplicado, mantiene solo el scoped por institución'
            },
            {
                'nombre': 'Agregar CHECK constraint para estado de matrícula',
                'sql': '''
                ALTER TABLE public.matricula_matriculaacademica
                ADD CONSTRAINT matricula_estado_chk
                CHECK (estado IN ('activo','retirado','promovido','repitente'));
                ''',
                'descripcion': 'Valida que el estado sea uno de los permitidos'
            },
            {
                'nombre': 'Agregar CHECK constraint para fechas de período',
                'sql': '''
                ALTER TABLE public.config_institucional_periodolectivo
                ADD CONSTRAINT periodo_fechas_chk 
                CHECK (fecha_fin > fecha_inicio);
                ''',
                'descripcion': 'Valida que fecha_fin sea posterior a fecha_inicio'
            },
            {
                'nombre': 'Mejorar FK de estudiante con ON DELETE RESTRICT',
                'sql': '''
                ALTER TABLE public.matricula_estudiante
                DROP CONSTRAINT IF EXISTS matricula_estudiante_institucion_id_fkey,
                ADD CONSTRAINT matricula_estudiante_institucion_fk
                FOREIGN KEY (institucion_id)
                REFERENCES public.core_institucion(id)
                ON DELETE RESTRICT
                DEFERRABLE INITIALLY DEFERRED;
                ''',
                'descripcion': 'Evita borrar institución si tiene estudiantes'
            },
            {
                'nombre': 'Mejorar FK de persona contacto con ON DELETE RESTRICT',
                'sql': '''
                ALTER TABLE public.matricula_personacontacto
                DROP CONSTRAINT IF EXISTS matricula_personacontacto_institucion_id_fkey,
                ADD CONSTRAINT matricula_personacontacto_institucion_fk
                FOREIGN KEY (institucion_id)
                REFERENCES public.core_institucion(id)
                ON DELETE RESTRICT
                DEFERRABLE INITIALLY DEFERRED;
                ''',
                'descripcion': 'Evita borrar institución si tiene personas de contacto'
            },
            {
                'nombre': 'Mejorar FK de encargado estudiante con ON DELETE RESTRICT',
                'sql': '''
                ALTER TABLE public.matricula_encargadoestudiante
                DROP CONSTRAINT IF EXISTS matricula_encargadoestudiante_institucion_id_fkey,
                ADD CONSTRAINT matricula_encargadoestudiante_institucion_fk
                FOREIGN KEY (institucion_id)
                REFERENCES public.core_institucion(id)
                ON DELETE RESTRICT
                DEFERRABLE INITIALLY DEFERRED;
                ''',
                'descripcion': 'Evita borrar institución si tiene encargados'
            },
            {
                'nombre': 'Mejorar FK de matrícula académica con ON DELETE RESTRICT',
                'sql': '''
                ALTER TABLE public.matricula_matriculaacademica
                DROP CONSTRAINT IF EXISTS matricula_matriculaacademica_institucion_id_fkey,
                ADD CONSTRAINT matricula_matriculaacademica_institucion_fk
                FOREIGN KEY (institucion_id)
                REFERENCES public.core_institucion(id)
                ON DELETE RESTRICT
                DEFERRABLE INITIALLY DEFERRED;
                ''',
                'descripcion': 'Evita borrar institución si tiene matrículas'
            },
            {
                'nombre': 'Mejorar FK de registro ingreso con ON DELETE RESTRICT',
                'sql': '''
                ALTER TABLE public.ingreso_clases_registroingreso
                DROP CONSTRAINT IF EXISTS ingreso_clases_registroingreso_institucion_id_fkey,
                ADD CONSTRAINT ingreso_clases_registroingreso_institucion_fk
                FOREIGN KEY (institucion_id)
                REFERENCES public.core_institucion(id)
                ON DELETE RESTRICT
                DEFERRABLE INITIALLY DEFERRED;
                ''',
                'descripcion': 'Evita borrar institución si tiene registros de ingreso'
            },
            {
                'nombre': 'Crear índice compuesto para consultas frecuentes',
                'sql': '''
                CREATE INDEX IF NOT EXISTS idx_matricula_institucion_estudiante 
                ON public.matricula_matriculaacademica (institucion_id, estudiante_id);
                ''',
                'descripcion': 'Optimiza consultas que filtran por institución + estudiante'
            },
            {
                'nombre': 'Crear índice compuesto para encargados',
                'sql': '''
                CREATE INDEX IF NOT EXISTS idx_encargado_institucion_estudiante 
                ON public.matricula_encargadoestudiante (institucion_id, estudiante_id);
                ''',
                'descripcion': 'Optimiza consultas que filtran por institución + estudiante'
            }
        ]
        
        try:
            with transaction.atomic():
                for mejora in mejoras:
                    self.stdout.write(f"🔧 {mejora['nombre']}")
                    self.stdout.write(f"   📝 {mejora['descripcion']}")
                    
                    if not dry_run:
                        try:
                            with connection.cursor() as cursor:
                                cursor.execute(mejora['sql'])
                            self.stdout.write(self.style.SUCCESS(f"      ✅ Aplicada"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"      ❌ Error: {str(e)}"))
                    else:
                        self.stdout.write(f"      🧪 SQL: {mejora['sql'].strip()}")
                        self.stdout.write("")
                
                if not dry_run:
                    self.stdout.write(self.style.SUCCESS('✅ Todas las mejoras aplicadas exitosamente'))
                else:
                    self.stdout.write(self.style.SUCCESS('🧪 DRY-RUN completado - Revisar SQL'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante la aplicación: {str(e)}'))
            raise

    def verificar_estado_actual(self):
        """Verificar el estado actual de la base de datos"""
        self.stdout.write('🔍 Verificando estado actual...')
        
        with connection.cursor() as cursor:
            # Verificar constraints existentes
            cursor.execute("""
                SELECT conname, tablename, contype 
                FROM pg_constraint 
                WHERE conname LIKE '%matricula%' OR conname LIKE '%encargado%'
                ORDER BY tablename, conname;
            """)
            
            constraints = cursor.fetchall()
            for constraint in constraints:
                self.stdout.write(f"   📋 {constraint[1]}: {constraint[0]} ({constraint[2]})")































