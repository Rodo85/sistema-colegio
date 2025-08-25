# Generated manually to fix institution field issue

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('matricula', '0001_initial'),
    ]

    operations = [
        # Verificar si existe el campo institución y removerlo si es necesario
        migrations.RunSQL(
            # SQL para PostgreSQL - verificar si existe la columna
            sql="""
            DO $$
            BEGIN
                -- Verificar si existe la columna institución
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'matricula_matriculaacademica' 
                    AND column_name = 'institucion_id'
                ) THEN
                    -- Remover la columna si existe
                    ALTER TABLE matricula_matriculaacademica DROP COLUMN IF EXISTS institucion_id;
                    RAISE NOTICE 'Columna institución removida de matricula_matriculaacademica';
                ELSE
                    RAISE NOTICE 'Columna institución no existe en matricula_matriculaacademica';
                END IF;
            END $$;
            """,
            reverse_sql="""
            -- No hacer nada en reverso, ya que estamos removiendo una columna incorrecta
            """
        ),
        
        # Agregar constraint para asegurar que no haya duplicados de matrícula activa por año
        migrations.RunSQL(
            sql="""
            -- Agregar constraint si no existe
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
                END IF;
            END $$;
            """,
            reverse_sql="""
            -- Remover constraint en reverso
            ALTER TABLE matricula_matriculaacademica 
            DROP CONSTRAINT IF EXISTS uniq_matricula_activa_por_anio;
            """
        ),
    ]