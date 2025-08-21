# matricula/management/commands/load_contactos.py
import os
import csv
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from matricula.models import PersonaContacto
from core.models import Institucion
from catalogos.models import EstadoCivil, Parentesco, Escolaridad, Ocupacion, TipoIdentificacion

class Command(BaseCommand):
    help = "Carga contactos desde el archivo contactos.csv"

    def handle(self, *args, **options):
        path = os.path.join(settings.BASE_DIR, 'contactos.csv')
        
        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"Archivo no encontrado: {path}"))
            return
        
        # Contadores
        creados = 0
        actualizados = 0
        errores = 0
        
        with transaction.atomic():
            with open(path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                for i, row in enumerate(reader, 1):
                    try:
                        # Debug: mostrar la fila actual
                        self.stdout.write(f"Procesando fila {i}: {row}")
                        
                        # Obtener la institución
                        institucion = Institucion.objects.get(id=row['intitucion_id'])
                        
                        # Obtener el tipo de identificación
                        tipo_identificacion = TipoIdentificacion.objects.get(id=row['tipo_identificacion'])
                        
                        # Obtener catálogos
                        estado_civil = EstadoCivil.objects.get(id=row['estado_civil_id'])
                        parentesco = Parentesco.objects.get(id=row['id_Parentesco_contacto'])
                        escolaridad = Escolaridad.objects.get(id=row['escolaridad_id'])
                        ocupacion = Ocupacion.objects.get(id=row['ocupacion_id'])
                        
                        # Limpiar datos
                        identificacion = row['identificacion'].strip() if row['identificacion'] else ''
                        primer_apellido = row['primer_apellido'].strip().upper() if row['primer_apellido'] else ''
                        segundo_apellido = row['segundo_apellido'].strip().upper() if row['segundo_apellido'] else ''
                        nombres = row['nombres'].strip().upper() if row['nombres'] else ''
                        celular = row['celular_avisos'].strip() if row['celular_avisos'] else ''
                        correo = row['correo'].strip().lower() if row['correo'] else ''
                        lugar_trabajo = row['lugar_trabajo'].strip().upper() if row['lugar_trabajo'] else ''
                        telefono_trabajo = row['telefono_trabajo'].strip() if row['telefono_trabajo'] else ''
                        
                        # Validar datos mínimos
                        if not identificacion or not primer_apellido or not nombres:
                            self.stdout.write(f"Fila {i}: Datos insuficientes, saltando...")
                            continue
                        
                        # Crear o actualizar contacto
                        contacto, created = PersonaContacto.objects.update_or_create(
                            institucion=institucion,
                            identificacion=identificacion,
                            defaults={
                                'tipo_identificacion': tipo_identificacion,
                                'primer_apellido': primer_apellido,
                                'segundo_apellido': segundo_apellido,
                                'nombres': nombres,
                                'celular_avisos': celular,
                                'correo': correo,
                                'lugar_trabajo': lugar_trabajo,
                                'telefono_trabajo': telefono_trabajo,
                                'estado_civil': estado_civil,
                                'escolaridad': escolaridad,
                                'ocupacion': ocupacion,
                            }
                        )
                        
                        if created:
                            creados += 1
                        else:
                            actualizados += 1
                            
                    except Exception as e:
                        errores += 1
                        self.stdout.write(f"Error en fila {i}: {str(e)}")
                        self.stdout.write(f"Contenido de la fila: {row}")
                        continue
        
        self.stdout.write(self.style.SUCCESS(
            f"Contactos cargados: {creados} creados, {actualizados} actualizados, {errores} errores"
        ))

