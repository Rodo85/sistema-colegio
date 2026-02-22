from django.db import migrations


class Migration(migrations.Migration):
    """
    Registra los permisos personalizados de cada modelo en el estado de migraciones.
    Las tablas ya existen; solo actualiza los metadatos de opciones.
    """

    dependencies = [
        ("evaluaciones", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="componenteeval",
            options={
                "db_table": "eval_component",
                "ordering": ("nombre",),
                "permissions": [
                    ("access_eval_components", "Puede gestionar componentes de evaluación"),
                ],
                "verbose_name": "Componente de evaluación",
                "verbose_name_plural": "Componentes de evaluación",
            },
        ),
        migrations.AlterModelOptions(
            name="esquemaeval",
            options={
                "db_table": "eval_scheme",
                "ordering": ("tipo", "nombre"),
                "permissions": [
                    ("access_eval_schemes", "Puede gestionar esquemas de evaluación"),
                ],
                "verbose_name": "Esquema de evaluación",
                "verbose_name_plural": "Esquemas de evaluación",
            },
        ),
        migrations.AlterModelOptions(
            name="subareacursolectivo",
            options={
                "db_table": "config_institucional_subareacursolectivo",
                "ordering": ("curso_lectivo__anio", "subarea__nombre"),
                "permissions": [
                    ("access_subareas_curso", "Puede gestionar subáreas por curso lectivo"),
                ],
                "verbose_name": "Subárea por Curso Lectivo",
                "verbose_name_plural": "Subáreas por Curso Lectivo",
            },
        ),
        migrations.AlterModelOptions(
            name="periodocursolectivo",
            options={
                "db_table": "config_institucional_periodocursolectivo",
                "ordering": ("curso_lectivo__anio", "periodo__numero"),
                "permissions": [
                    ("access_periodos_curso", "Puede gestionar períodos por curso lectivo"),
                ],
                "verbose_name": "Período por Curso Lectivo",
                "verbose_name_plural": "Períodos por Curso Lectivo",
            },
        ),
        migrations.AlterModelOptions(
            name="docenteasignacion",
            options={
                "db_table": "docente_asignacion",
                "ordering": ("-curso_lectivo__anio", "docente__usuario__last_name"),
                "permissions": [
                    ("access_docente_asignacion", "Puede gestionar asignaciones docentes"),
                ],
                "verbose_name": "Asignación Docente",
                "verbose_name_plural": "Asignaciones Docentes",
            },
        ),
    ]
