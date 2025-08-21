# matricula/management/commands/load_estudiantes.py
import os
import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from matricula.models import Estudiante
from core.models import Institucion
from catalogos.models import (
    TipoIdentificacion, Sexo, Nacionalidad, Provincia, Canton, Distrito, Adecuacion
)

class Command(BaseCommand):
    help = "Carga estudiantes desde el archivo estudiantes.csv"

    def handle(self, *args, **options):
        path = os.path.join(settings.BASE_DIR, 'estudiantes.csv')
        
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
                        institucion = Institucion.objects.get(id=row['institucion_id'])
                        
                        # Obtener el tipo de identificación
                        tipo_identificacion = TipoIdentificacion.objects.get(id=row['tipo_identificacion_id'])
                        
                        # Obtener catálogos
                        sexo = Sexo.objects.get(id=row['sexo_id'])
                        nacionalidad = Nacionalidad.objects.get(id=row['nacionalidad_id'])
                        provincia = Provincia.objects.get(id=row['provincia_id'])
                        
                        # Canton y distrito pueden ser opcionales
                        canton = None
                        if row['canton_id'] and row['canton_id'].strip():
                            canton = Canton.objects.get(id=row['canton_id'])
                        
                        distrito = None
                        if row['distrito_id'] and row['distrito_id'].strip():
                            distrito = Distrito.objects.get(id=row['distrito_id'])
                        
                        # Adecuacion puede ser opcional
                        adecuacion = None
                        if row['adecuacion_id'] and row['adecuacion_id'].strip():
                            adecuacion = Adecuacion.objects.get(id=row['adecuacion_id'])
                        
                        # Limpiar datos
                        identificacion = row['identificacion'].strip() if row['identificacion'] else ''
                        primer_apellido = row['primer_apellido'].strip().upper() if row['primer_apellido'] else ''
                        segundo_apellido = row['segundo_apellido'].strip().upper() if row['segundo_apellido'] else ''
                        nombres = row['nombres'].strip().upper() if row['nombres'] else ''
                        celular = row['celular'].strip() if row['celular'] else ''
                        telefono_casa = row['telefono_casa'].strip() if row['telefono_casa'] else ''
                        direccion_exacta = row['direccion_exacta'].strip().upper() if row['direccion_exacta'] else ''
                        correo = row['correo'].strip().lower() if row['correo'] else ''
                        numero_poliza = row['numero_poliza'].strip() if row['numero_poliza'] else ''
                        detalle_enfermedad = row['detalle_enfermedad'].strip().upper() if row['detalle_enfermedad'] else ''
                        medicamento_consume = row['medicamentos_consume'].strip() if row['medicamentos_consume'] else ''
                        
                        # Procesar fecha de nacimiento
                        fecha_nacimiento = None
                        if row['fecha_nacimiento'] and row['fecha_nacimiento'].strip():
                            try:
                                fecha_nacimiento = datetime.strptime(row['fecha_nacimiento'], '%d/%m/%Y').date()
                            except ValueError:
                                self.stdout.write(f"Fila {i}: Formato de fecha inválido: {row['fecha_nacimiento']}")
                                continue
                        
                        # Procesar fechas de póliza
                        rige_poliza = None
                        if row['rige_poliza'] and row['rige_poliza'].strip():
                            try:
                                rige_poliza = datetime.strptime(row['rige_poliza'], '%d/%m/%Y').date()
                            except ValueError:
                                pass
                        
                        vence_poliza = None
                        if row['vence_poliza'] and row['vence_poliza'].strip():
                            try:
                                vence_poliza = datetime.strptime(row['vence_poliza'], '%d/%m/%Y').date()
                            except ValueError:
                                pass
                        
                        # Procesar campos booleanos
                        ed_religiosa = row['ed_religiosa'].lower() == 'true' if row['ed_religiosa'] else False
                        presenta_enfermedad = row['presenta_enfermedad'].lower() == 'true' if row['presenta_enfermedad'] else False
                        autoriza_derecho_imagen = row['autoriza_derecho_imagen'].lower() == 'true' if row['autoriza_derecho_imagen'] else False
                        
                        # Validar datos mínimos
                        if not identificacion or not primer_apellido or not nombres or not fecha_nacimiento:
                            self.stdout.write(f"Fila {i}: Datos insuficientes, saltando...")
                            continue
                        
                        # Crear o actualizar estudiante
                        estudiante, created = Estudiante.objects.update_or_create(
                            institucion=institucion,
                            identificacion=identificacion,
                            defaults={
                                'tipo_estudiante': row['tipo_estudiante'],
                                'tipo_identificacion': tipo_identificacion,
                                'primer_apellido': primer_apellido,
                                'segundo_apellido': segundo_apellido,
                                'nombres': nombres,
                                'fecha_nacimiento': fecha_nacimiento,
                                'celular': celular,
                                'telefono_casa': telefono_casa,
                                'sexo': sexo,
                                'nacionalidad': nacionalidad,
                                'provincia': provincia,
                                'canton': canton,
                                'distrito': distrito,
                                'direccion_exacta': direccion_exacta,
                                'correo': correo,
                                'ed_religiosa': ed_religiosa,
                                'rige_poliza': rige_poliza,
                                'vence_poliza': vence_poliza,
                                'presenta_enfermedad': presenta_enfermedad,
                                'detalle_enfermedad': detalle_enfermedad,
                                'numero_poliza': numero_poliza,
                                'adecuacion': adecuacion,
                                'medicamento_consume': medicamento_consume,
                                'autoriza_derecho_imagen': autoriza_derecho_imagen,
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
            f"Estudiantes cargados: {creados} creados, {actualizados} actualizados, {errores} errores"
        ))
