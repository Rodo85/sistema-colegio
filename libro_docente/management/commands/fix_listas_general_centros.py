from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from evaluaciones.models import DocenteAsignacion
from libro_docente.models import ListaEstudiantesDocente, ListaEstudiantesDocenteItem


class Command(BaseCommand):
    help = (
        "Alinea listas privadas legacy (sin centro_trabajo) con el centro de trabajo "
        "de asignaciones activas en Institucion General."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica cambios en base de datos. Sin este flag solo reporta (dry-run).",
        )
        parser.add_argument(
            "--docente-id",
            type=int,
            default=None,
            help="Opcional: limita el proceso a un docente (Profesor.id).",
        )

    def handle(self, *args, **options):
        self._validar_esquema_minimo()
        apply_changes = bool(options.get("apply"))
        docente_id = options.get("docente_id")

        self.stdout.write("Iniciando analisis de listas legacy (sin centro_trabajo)...")
        if apply_changes:
            self.stdout.write(self.style.WARNING("MODO APPLY: se realizaran cambios."))
        else:
            self.stdout.write(self.style.WARNING("MODO DRY-RUN: no se guardaran cambios."))

        asignaciones_qs = (
            DocenteAsignacion.objects
            .filter(
                activo=True,
                subarea_curso__institucion__es_institucion_general=True,
                centro_trabajo__isnull=False,
            )
            .select_related("subarea_curso__institucion", "docente", "curso_lectivo")
            .order_by("id")
        )
        if docente_id:
            asignaciones_qs = asignaciones_qs.filter(docente_id=docente_id)

        # Se agrupa por clave de lista, ignorando subarea.
        grupos = {}
        centros_por_grupo = defaultdict(set)
        for a in asignaciones_qs:
            clave = (
                a.docente_id,
                a.subarea_curso.institucion_id,
                a.curso_lectivo_id,
                a.seccion_id,
                a.subgrupo_id,
            )
            grupos[clave] = a
            centros_por_grupo[clave].add(a.centro_trabajo_id)

        total_grupos = len(grupos)
        self.stdout.write(f"Grupos detectados: {total_grupos}")

        stats = {
            "sin_legacy": 0,
            "ambiguo_centros": 0,
            "sin_destino_creado": 0,
            "target_existia": 0,
            "target_creado": 0,
            "legacy_actualizada_centro": 0,
            "items_movidos": 0,
            "grupos_aplicados": 0,
            "grupos_sin_cambios": 0,
        }

        def _procesar():
            for clave, asignacion_ref in grupos.items():
                docente_id_, institucion_id, curso_id, seccion_id, subgrupo_id = clave
                centros = centros_por_grupo[clave]
                if len(centros) != 1:
                    stats["ambiguo_centros"] += 1
                    continue
                destino_centro_id = next(iter(centros))

                filtros_base = {
                    "docente_id": docente_id_,
                    "institucion_id": institucion_id,
                    "curso_lectivo_id": curso_id,
                    "seccion_id": seccion_id,
                    "subgrupo_id": subgrupo_id,
                }
                legacy_qs = ListaEstudiantesDocente.objects.filter(
                    **filtros_base,
                    centro_trabajo__isnull=True,
                ).order_by("id")
                legacy_listas = list(legacy_qs)
                if not legacy_listas:
                    stats["sin_legacy"] += 1
                    continue

                target = ListaEstudiantesDocente.objects.filter(
                    **filtros_base,
                    centro_trabajo_id=destino_centro_id,
                ).first()
                if target:
                    stats["target_existia"] += 1
                else:
                    # Caso seguro: si existe una sola lista legacy, se puede reasignar.
                    if len(legacy_listas) == 1:
                        legacy = legacy_listas[0]
                        legacy.centro_trabajo_id = destino_centro_id
                        if apply_changes:
                            legacy.save(update_fields=["centro_trabajo", "updated_at"])
                        stats["legacy_actualizada_centro"] += 1
                        stats["target_creado"] += 1
                        stats["grupos_aplicados"] += 1
                        continue

                    # Si hay multiples listas legacy, crear target y fusionar items.
                    target = ListaEstudiantesDocente(
                        docente_id=docente_id_,
                        institucion_id=institucion_id,
                        curso_lectivo_id=curso_id,
                        seccion_id=seccion_id,
                        subgrupo_id=subgrupo_id,
                        centro_trabajo_id=destino_centro_id,
                        created_by_id=legacy_listas[0].created_by_id,
                    )
                    if apply_changes:
                        target.save()
                    stats["target_creado"] += 1
                    if not apply_changes:
                        stats["sin_destino_creado"] += 1
                        stats["grupos_aplicados"] += 1
                        continue

                # Fusion de items legacy hacia target (sin duplicar estudiante).
                if not apply_changes:
                    stats["grupos_aplicados"] += 1
                    continue

                existentes = set(
                    ListaEstudiantesDocenteItem.objects.filter(lista=target).values_list(
                        "estudiante_id", flat=True
                    )
                )
                max_orden = (
                    ListaEstudiantesDocenteItem.objects.filter(lista=target)
                    .order_by("-orden")
                    .values_list("orden", flat=True)
                    .first()
                    or 0
                )
                nuevos = []
                for legacy in legacy_listas:
                    items = list(
                        legacy.items.order_by("orden", "id").values_list("estudiante_id", "orden")
                    )
                    for est_id, _orden in items:
                        if est_id in existentes:
                            continue
                        max_orden += 1
                        existentes.add(est_id)
                        nuevos.append(
                            ListaEstudiantesDocenteItem(
                                lista=target,
                                estudiante_id=est_id,
                                orden=max_orden,
                            )
                        )
                if nuevos:
                    ListaEstudiantesDocenteItem.objects.bulk_create(nuevos)
                    stats["items_movidos"] += len(nuevos)
                stats["grupos_aplicados"] += 1

        if apply_changes:
            with transaction.atomic():
                _procesar()
        else:
            _procesar()

        stats["grupos_sin_cambios"] = (
            total_grupos
            - stats["grupos_aplicados"]
            - stats["sin_legacy"]
            - stats["ambiguo_centros"]
        )

        self.stdout.write("")
        self.stdout.write("Resumen:")
        self.stdout.write(f"- Grupos totales: {total_grupos}")
        self.stdout.write(f"- Sin lista legacy: {stats['sin_legacy']}")
        self.stdout.write(f"- Ambiguos por centros: {stats['ambiguo_centros']}")
        self.stdout.write(f"- Target ya existia: {stats['target_existia']}")
        self.stdout.write(f"- Target creado: {stats['target_creado']}")
        self.stdout.write(f"- Legacy actualizada con centro: {stats['legacy_actualizada_centro']}")
        self.stdout.write(f"- Items movidos a target: {stats['items_movidos']}")
        self.stdout.write(f"- Grupos aplicados: {stats['grupos_aplicados']}")
        self.stdout.write(f"- Grupos sin cambios: {stats['grupos_sin_cambios']}")

        if apply_changes:
            self.stdout.write(self.style.SUCCESS("Proceso finalizado con cambios aplicados."))
        else:
            self.stdout.write(self.style.SUCCESS("Dry-run finalizado sin cambios."))

    def _validar_esquema_minimo(self):
        with connection.cursor() as cursor:
            cols_asig = {
                c.name for c in connection.introspection.get_table_description(cursor, "docente_asignacion")
            }
            cols_lista = {
                c.name
                for c in connection.introspection.get_table_description(
                    cursor, "libro_docente_lista_estudiantes_docente"
                )
            }
        if "centro_trabajo_id" not in cols_asig:
            raise CommandError(
                "La tabla docente_asignacion no tiene centro_trabajo_id. "
                "Ejecuta migraciones pendientes antes de correr este comando."
            )
        if "centro_trabajo_id" not in cols_lista:
            raise CommandError(
                "La tabla libro_docente_lista_estudiantes_docente no tiene centro_trabajo_id. "
                "Ejecuta migraciones pendientes antes de correr este comando."
            )
