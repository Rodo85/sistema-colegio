from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("libro_docente", "0013_asistenciaregistro_lecciones_injustificadas"),
    ]

    operations = [
        migrations.CreateModel(
            name="ListaEstudiantesDocente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="listas_estudiantes_docente_creadas",
                        to="core.user",
                        verbose_name="Creado por",
                    ),
                ),
                (
                    "curso_lectivo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="listas_estudiantes_docente",
                        to="catalogos.cursolectivo",
                        verbose_name="Curso lectivo",
                    ),
                ),
                (
                    "docente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="listas_estudiantes_docente",
                        to="config_institucional.profesor",
                        verbose_name="Docente",
                    ),
                ),
                (
                    "institucion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="listas_estudiantes_docente",
                        to="core.institucion",
                        verbose_name="Institución",
                    ),
                ),
                (
                    "seccion",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="listas_estudiantes_docente",
                        to="catalogos.seccion",
                        verbose_name="Sección",
                    ),
                ),
                (
                    "subgrupo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="listas_estudiantes_docente",
                        to="catalogos.subgrupo",
                        verbose_name="Subgrupo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lista privada de estudiantes (docente)",
                "verbose_name_plural": "Listas privadas de estudiantes (docente)",
                "db_table": "libro_docente_lista_estudiantes_docente",
            },
        ),
        migrations.CreateModel(
            name="ListaEstudiantesDocenteItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("orden", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "estudiante",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="listas_docente_items",
                        to="matricula.estudiante",
                        verbose_name="Estudiante",
                    ),
                ),
                (
                    "lista",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="libro_docente.listaestudiantesdocente",
                        verbose_name="Lista",
                    ),
                ),
            ],
            options={
                "verbose_name": "Estudiante en lista privada",
                "verbose_name_plural": "Estudiantes en lista privada",
                "db_table": "libro_docente_lista_estudiantes_docente_item",
                "ordering": ("orden", "id"),
            },
        ),
        migrations.AddConstraint(
            model_name="listaestudiantesdocente",
            constraint=models.UniqueConstraint(
                condition=models.Q(seccion__isnull=False, subgrupo__isnull=True),
                fields=("docente", "curso_lectivo", "seccion"),
                name="uniq_libdoc_lista_doc_curso_seccion",
            ),
        ),
        migrations.AddConstraint(
            model_name="listaestudiantesdocente",
            constraint=models.UniqueConstraint(
                condition=models.Q(subgrupo__isnull=False),
                fields=("docente", "curso_lectivo", "subgrupo"),
                name="uniq_libdoc_lista_doc_curso_subgrupo",
            ),
        ),
        migrations.AddConstraint(
            model_name="listaestudiantesdocenteitem",
            constraint=models.UniqueConstraint(
                fields=("lista", "estudiante"),
                name="uniq_libdoc_lista_item",
            ),
        ),
    ]
