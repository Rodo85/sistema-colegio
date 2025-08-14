from django.core.management.base import BaseCommand
from django.db import transaction
from config_institucional.models import Seccion as SeccionLocal, Subgrupo as SubgrupoLocal
from catalogos.models import Seccion as SeccionGlobal, Subgrupo as SubgrupoGlobal


class Command(BaseCommand):
    help = 'Migra datos de secciones y subgrupos locales a catálogos globales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirmar que desea ejecutar la migración',
        )

    def handle(self, *args, **options):
        if not options['confirmar']:
            self.stdout.write(
                self.style.WARNING('⚠️ Este comando migrará datos. Use --confirmar para ejecutar.')
            )
            return

        with transaction.atomic():
            self.stdout.write('🚀 Iniciando migración...')
            
            # 1. Migrar secciones
            secciones_migradas = 0
            for seccion_local in SeccionLocal.objects.all():
                seccion_global, created = SeccionGlobal.objects.get_or_create(
                    nivel=seccion_local.nivel,
                    numero=seccion_local.numero
                )
                if created:
                    secciones_migradas += 1
                    self.stdout.write(f'✅ Sección creada: {seccion_global}')

            # 2. Migrar subgrupos
            subgrupos_migrados = 0
            for subgrupo_local in SubgrupoLocal.objects.all():
                # Encontrar la sección global correspondiente
                try:
                    seccion_global = SeccionGlobal.objects.get(
                        nivel=subgrupo_local.seccion.nivel,
                        numero=subgrupo_local.seccion.numero
                    )
                    subgrupo_global, created = SubgrupoGlobal.objects.get_or_create(
                        seccion=seccion_global,
                        letra=subgrupo_local.letra
                    )
                    if created:
                        subgrupos_migrados += 1
                        self.stdout.write(f'✅ Subgrupo creado: {subgrupo_global}')
                except SeccionGlobal.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'❌ No se encontró sección global para: {subgrupo_local.seccion}')
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f'🎉 Migración completada:\n'
                    f'   - Secciones migradas: {secciones_migradas}\n'
                    f'   - Subgrupos migrados: {subgrupos_migrados}'
                )
            )

