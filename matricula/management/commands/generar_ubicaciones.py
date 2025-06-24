# matricula/management/commands/generar_ubicaciones.py
import csv
import os
import requests

from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Descarga y consolida Provincias, Cantones y Distritos en data/ubicaciones.csv"

    URLS = {
        "prov": "https://raw.githubusercontent.com/investigacion/divisiones-territoriales-data/master/data/csv/adm1-provincias.csv",
        "cant": "https://raw.githubusercontent.com/investigacion/divisiones-territoriales-data/master/data/csv/adm2-cantones.csv",
        "dist": "https://raw.githubusercontent.com/investigacion/divisiones-territoriales-data/master/data/csv/adm3-distritos.csv",
    }

    def _find_key(self, keys, candidates):
        """Busca en keys la primera que contenga alguna de las palabras de candidates."""
        for k in keys:
            low = k.lower()
            if any(c.lower() in low for c in candidates):
                return k
        raise KeyError(f"No encontré ninguna de {candidates} en {keys}")

    def handle(self, *args, **options):
        base = os.path.join(settings.BASE_DIR, "matricula", "data")
        os.makedirs(base, exist_ok=True)

        # 1) Descarga los CSVs
        data = {}
        for key, url in self.URLS.items():
            r = requests.get(url)
            r.encoding = 'utf-8'
            data[key] = list(csv.DictReader(r.text.splitlines()))

        # 2) Identificar cabeceras reales
        prov_keys = data["prov"][0].keys()
        prov_code_k = self._find_key(prov_keys, ["código", "code", "id"])
        prov_name_k = self._find_key(prov_keys, ["nombre", "name"])

        cant_keys = data["cant"][0].keys()
        cant_code_k = self._find_key(cant_keys, ["código", "code", "id"])
        cant_name_k = self._find_key(cant_keys, ["nombre", "name"])
        cant_prov_k = self._find_key(cant_keys, ["provincia", "prov"])

        dist_keys = data["dist"][0].keys()
        dist_name_k = self._find_key(dist_keys, ["nombre", "name"])
        dist_cant_k = self._find_key(dist_keys, ["canton", "cant"])

        # 3) Mapea provincias y cantones
        prov_map = {
            row[prov_code_k]: row[prov_name_k]
            for row in data["prov"]
        }
        cant_map = {
            row[cant_code_k]: {
                "nombre": row[cant_name_k],
                "prov_code": row[cant_prov_k]
            }
            for row in data["cant"]
        }

        # 4) Genera ubicaciones consolidadas
        out_path = os.path.join(base, "ubicaciones.csv")
        with open(out_path, "w", newline="", encoding="utf-8") as fout:
            writer = csv.writer(fout)
            writer.writerow(["provincia","canton","distrito"])
            for row in data["dist"]:
                distr_nombre = row[dist_name_k]
                canton_code = row[dist_cant_k]
                info_cant = cant_map.get(canton_code)
                if not info_cant:
                    continue
                provincia = prov_map.get(info_cant["prov_code"], "")
                canton = info_cant["nombre"]
                writer.writerow([provincia, canton, distr_nombre])

        self.stdout.write(self.style.SUCCESS(
            f"CSV generado en {out_path}"
        ))
