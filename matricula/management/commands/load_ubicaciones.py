# matricula/management/commands/load_ubicaciones.py
import os
import csv
from django.core.management.base import BaseCommand
from django.conf import settings
from catalogos.models import Provincia, Canton, Distrito

class Command(BaseCommand):
    help = "Carga provincias, cantones y distritos reales de CR"

    def handle(self, *args, **options):
        path = os.path.join(settings.BASE_DIR, 'matricula', 'data', 'ubicaciones.csv')
        
        # Limpiar datos existentes
        Distrito.objects.all().delete()
        Canton.objects.all().delete()
        Provincia.objects.all().delete()
        
        provincias = {}
        cantones = {}
        
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                # Procesar provincia
                if row['provincia'] not in provincias:
                    prov = Provincia.objects.create(nombre=row['provincia'])
                    provincias[row['provincia']] = prov
                
                # Procesar cantón
                canton_key = f"{row['provincia']}-{row['canton']}"
                if canton_key not in cantones:
                    canton = Canton.objects.create(
                        provincia=provincias[row['provincia']],
                        nombre=row['canton']
                    )
                    cantones[canton_key] = canton
                
                # Procesar distrito
                Distrito.objects.create(
                    canton=cantones[canton_key],
                    nombre=row['distrito']
                )
                
        self.stdout.write(self.style.SUCCESS(
            f"Datos cargados: {Provincia.objects.count()} provincias, "
            f"{Canton.objects.count()} cantones, "
            f"{Distrito.objects.count()} distritos"
        ))