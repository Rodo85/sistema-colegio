import os, csv
from django.core.management.base import BaseCommand
from django.conf import settings
from catalogos.models import Provincia, Canton, Distrito

class Command(BaseCommand):
    help = "Carga provincias, cantones y distritos desde data/ubicaciones.csv"

    def handle(self, *args, **options):
        path = os.path.join(settings.BASE_DIR, 'matricula', 'data', 'ubicaciones.csv')
        created = 0
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, fieldnames=['provincia','canton','distrito'])
            for row in reader:
                prov, _ = Provincia.objects.get_or_create(nombre=row['provincia'])
                cant, _ = Canton.objects.get_or_create(
                    provincia=prov,
                    nombre=row['canton']
                )
                dist, flag = Distrito.objects.get_or_create(
                    canton=cant,
                    nombre=row['distrito']
                )
                if flag:
                    created += 1
        self.stdout.write(self.style.SUCCESS(f"Distritos creados: {created}"))
