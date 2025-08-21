from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Crea manualmente la tabla matricula_encargadoestudiante'

    def handle(self, *args, **options):
        self.stdout.write('🔧 Creando tabla matricula_encargadoestudiante...')
        
        try:
            with connection.cursor() as cursor:
                # Crear la tabla
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS matricula_encargadoestudiante (
                        id BIGSERIAL PRIMARY KEY,
                        estudiante_id BIGINT NOT NULL,
                        persona_contacto_id BIGINT NOT NULL,
                        parentesco_id BIGINT NOT NULL,
                        convivencia BOOLEAN,
                        principal BOOLEAN NOT NULL DEFAULT FALSE,
                        CONSTRAINT matricula_encargadoestudiante_estudiante_id_fkey 
                            FOREIGN KEY (estudiante_id) REFERENCES matricula_estudiante(id) DEFERRABLE INITIALLY DEFERRED,
                        CONSTRAINT matricula_encargadoestudiante_persona_contacto_id_fkey 
                            FOREIGN KEY (persona_contacto_id) REFERENCES matricula_personacontacto(id) DEFERRABLE INITIALLY DEFERRED,
                        CONSTRAINT matricula_encargadoestudiante_parentesco_id_fkey 
                            FOREIGN KEY (parentesco_id) REFERENCES catalogos_parentesco(id) DEFERRABLE INITIALLY DEFERRED,
                        CONSTRAINT matricula_encargadoestudiante_estudiante_persona_contacto_parentesco_key 
                            UNIQUE (estudiante_id, persona_contacto_id, parentesco_id),
                        CONSTRAINT matricula_encargadoestudiante_unique_principal_por_estudiante 
                            UNIQUE (estudiante_id) WHERE (principal = true)
                    );
                """)
                
                # Crear índices para mejorar el rendimiento
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS matricula_encargadoestudiante_estudiante_id_idx 
                    ON matricula_encargadoestudiante(estudiante_id);
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS matricula_encargadoestudiante_persona_contacto_id_idx 
                    ON matricula_encargadoestudiante(persona_contacto_id);
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS matricula_encargadoestudiante_parentesco_id_idx 
                    ON matricula_encargadoestudiante(parentesco_id);
                """)
                
                self.stdout.write(self.style.SUCCESS('✅ Tabla matricula_encargadoestudiante creada exitosamente'))
                
                # Verificar que la tabla existe
                cursor.execute("SELECT COUNT(*) FROM matricula_encargadoestudiante")
                count = cursor.fetchone()[0]
                self.stdout.write(f'📊 La tabla contiene {count} registros')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error creando la tabla: {e}'))
            return
        
        # Verificar que Django puede acceder a la tabla
        try:
            from matricula.models import EncargadoEstudiante
            count = EncargadoEstudiante.objects.count()
            self.stdout.write(self.style.SUCCESS(f'✅ Django puede acceder a la tabla: {count} registros'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Django no puede acceder a la tabla: {e}'))

