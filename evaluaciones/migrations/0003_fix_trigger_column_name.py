from django.db import migrations


class Migration(migrations.Migration):
    """
    Corrige el nombre de columna en el trigger fn_eval_check_porcentaje_sum.
    El campo FK en EsquemaEvalComponente se llama 'esquema', por lo que Django
    genera la columna como 'esquema_id', no 'scheme_id'.
    """

    dependencies = [
        ("evaluaciones", "0002_add_permissions"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
CREATE OR REPLACE FUNCTION fn_eval_check_porcentaje_sum()
RETURNS TRIGGER AS $$
DECLARE
    v_scheme_id BIGINT;
    v_total     NUMERIC;
    v_locked    BOOLEAN;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_scheme_id := OLD.esquema_id;
    ELSE
        v_scheme_id := NEW.esquema_id;
    END IF;

    SELECT locked INTO v_locked
    FROM eval_scheme
    WHERE id = v_scheme_id;

    IF v_locked THEN
        SELECT COALESCE(SUM(porcentaje), 0) INTO v_total
        FROM eval_scheme_component
        WHERE esquema_id = v_scheme_id;

        IF v_total <> 100 THEN
            RAISE EXCEPTION
                'Esquema bloqueado: la suma de porcentajes debe ser 100 (actual: %).',
                v_total;
        END IF;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""",
            reverse_sql="-- no reverse needed; el trigger sigue activo con la función corregida",
        ),
    ]
