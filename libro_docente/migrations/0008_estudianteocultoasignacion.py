from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("evaluaciones", "0003_fix_trigger_column_name"),
        ("matricula", "0004_alter_matriculaacademica_options"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("libro_docente", "0007_actividad_simple_prueba_proyecto"),
    ]

    operations = [
        migrations.CreateModel(
            name="EstudianteOcultoAsignacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ocultamientos_estudiantes_libro_docente", to=settings.AUTH_USER_MODEL, verbose_name="Creado por")),
                ("docente_asignacion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="estudiantes_ocultos", to="evaluaciones.docenteasignacion", verbose_name="Asignación docente")),
                ("estudiante", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ocultamientos_libro_docente", to="matricula.estudiante", verbose_name="Estudiante")),
            ],
            options={
                "verbose_name": "Estudiante oculto por asignación",
                "verbose_name_plural": "Estudiantes ocultos por asignación",
                "db_table": "libro_docente_estudiante_oculto",
            },
        ),
        migrations.AddConstraint(
            model_name="estudianteocultoasignacion",
            constraint=models.UniqueConstraint(fields=("docente_asignacion", "estudiante"), name="uniq_libro_doc_est_oculto"),
        ),
        migrations.AddIndex(
            model_name="estudianteocultoasignacion",
            index=models.Index(fields=["docente_asignacion", "estudiante"], name="libro_doc_est_oc_idx"),
        ),
    ]
