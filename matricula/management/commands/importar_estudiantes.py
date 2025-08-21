from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import pandas as pd
from datetime import datetime
import re

from matricula.models import Estudiante
from catalogos.models import Nacionalidad, Sexo, Parentesco, Escolaridad, Ocupacion, Provincia, Canton, Distrito, TipoIdentificacion
from core.models import Institucion

class Command(BaseCommand):
    help = 'Importar estudiantes desde un archivo Excel (.xlsx, .xls) o CSV'

    def add_arguments(self, parser):
        parser.add_argument('archivo', type=str, help='Ruta al archivo Excel (.xlsx, .xls) o CSV')
        parser.add_argument('--institucion', type=int, help='ID de la institución')
        parser.add_argument('--dry-run', action='store_true', help='Solo validar, no guardar')

    def handle(self, *args, **options):
        archivo = options['archivo']
        institucion_id = options['institucion']
        dry_run = options['dry_run']

        try:
            # Leer el archivo (Excel o CSV)
            self.stdout.write(f"Leyendo archivo: {archivo}")
            
            if archivo.endswith('.csv'):
                df = pd.read_csv(archivo)
            else:
                df = pd.read_excel(archivo)
            
            # Validar columnas requeridas
            self.validar_columnas(df)
            
            # Obtener institución
            institucion = self.obtener_institucion(institucion_id)
            
            # Procesar datos
            resultados = self.procesar_estudiantes(df, institucion, dry_run)
            
            # Mostrar resultados
            self.mostrar_resultados(resultados, dry_run)
            
        except Exception as e:
            raise CommandError(f"Error al procesar el archivo: {str(e)}")

    def validar_columnas(self, df):
        """Validar que el archivo tenga las columnas requeridas"""
        # Mapeo de columnas requeridas con posibles variaciones
        mapeo_columnas = {
            'cedula de estudiante': ['cedula de estudiante', 'cedula estudiante', 'cedula', 'cédula'],
            '1er apellido estudiante': ['1er apellido estudiante', '1er apellido', 'primer apellido', 'apellido1'],
            '2do apellido estudiante': ['2do apellido estudiante', '2do apellido', 'segundo apellido', 'apellido2'],
            'Nombre estudiante2': ['Nombre estudiante2', 'Nombre estudiante', 'nombres', 'nombre'],
            'Fecha nacimiento': ['Fecha nacimiento', 'fecha nacimiento', 'fecha_nacimiento', 'nacimiento'],
            'id_Genero': ['id_Genero', 'id_genero', 'genero', 'género', 'sexo'],
            'id_nacionalidad': ['id_nacionalidad', 'nacionalidad', 'pais', 'país']
        }
        
        # Verificar que al menos una variación de cada columna requerida esté presente
        columnas_encontradas = {}
        columnas_faltantes = []
        
        for col_requerida, variaciones in mapeo_columnas.items():
            col_encontrada = None
            for variacion in variaciones:
                if variacion in df.columns:
                    col_encontrada = variacion
                    break
            
            if col_encontrada:
                columnas_encontradas[col_requerida] = col_encontrada
            else:
                columnas_faltantes.append(col_requerida)
        
        if columnas_faltantes:
            raise CommandError(f"Columnas faltantes: {', '.join(columnas_faltantes)}")
        
        # Guardar el mapeo para usar en procesar_fila
        self.mapeo_columnas = columnas_encontradas
        
        self.stdout.write(f"✅ Archivo válido con {len(df)} filas")
        self.stdout.write(f"📋 Columnas mapeadas: {columnas_encontradas}")

    def obtener_institucion(self, institucion_id):
        """Obtener la institución para la importación"""
        if institucion_id:
            try:
                return Institucion.objects.get(id=institucion_id)
            except Institucion.DoesNotExist:
                raise CommandError(f"Institución con ID {institucion_id} no existe")
        else:
            # Usar la primera institución disponible
            institucion = Institucion.objects.first()
            if not institucion:
                raise CommandError("No hay instituciones disponibles")
            self.stdout.write(f"Usando institución: {institucion.nombre}")
            return institucion

    def procesar_estudiantes(self, df, institucion, dry_run):
        """Procesar cada estudiante del Excel"""
        resultados = {
            'total': len(df),
            'validos': 0,
            'errores': [],
            'duplicados': 0,
            'creados': 0,
            'actualizados': 0
        }

        for index, row in df.iterrows():
            try:
                # Validar y procesar fila
                estudiante_data = self.procesar_fila(row, institucion)
                
                if not estudiante_data:
                    continue

                # Verificar si ya existe
                if Estudiante.objects.filter(identificacion=estudiante_data['cedula']).exists():
                    resultados['duplicados'] += 1
                    if not dry_run:
                        # Actualizar estudiante existente
                        self.actualizar_estudiante(estudiante_data)
                        resultados['actualizados'] += 1
                    resultados['validos'] += 1
                else:
                    if not dry_run:
                        # Crear nuevo estudiante
                        self.crear_estudiante(estudiante_data)
                        resultados['creados'] += 1
                    resultados['validos'] += 1

            except Exception as e:
                error_msg = f"Fila {index + 2}: {str(e)}"
                resultados['errores'].append(error_msg)
                self.stdout.write(f"❌ {error_msg}")

        return resultados

    def procesar_fila(self, row, institucion):
        """Procesar una fila individual del Excel"""
        try:
            # Extraer y limpiar datos básicos usando el mapeo
            cedula = str(row[self.mapeo_columnas['cedula de estudiante']]).strip()
            if pd.isna(cedula) or cedula == '':
                return None

            # Validar cédula
            if not self.validar_cedula(cedula):
                raise ValueError(f"Cédula inválida: {cedula}")

            # Procesar nombres
            primer_apellido = str(row[self.mapeo_columnas['1er apellido estudiante']]).strip()
            segundo_apellido = str(row[self.mapeo_columnas['2do apellido estudiante']]).strip()
            nombre = str(row[self.mapeo_columnas['Nombre estudiante2']]).strip()

            if pd.isna(primer_apellido) or pd.isna(nombre):
                raise ValueError("Primer apellido y nombre son obligatorios")

            # Procesar tipo de identificación (por defecto: Cédula)
            tipo_identificacion = self.procesar_tipo_identificacion('Cédula')

            # Procesar fecha de nacimiento
            fecha_nac = self.procesar_fecha(row[self.mapeo_columnas['Fecha nacimiento']])
            
            # Procesar género
            genero = self.procesar_genero(row[self.mapeo_columnas['id_Genero']])
            
            # Procesar nacionalidad
            nacionalidad = self.procesar_nacionalidad(row[self.mapeo_columnas['id_nacionalidad']])

            # Procesar ubicación (columnas opcionales)
            provincia = None
            canton = None
            distrito = None
            direccion = ''
            
            # Intentar procesar ubicación si las columnas existen
            if 'Provincia Residencia' in row.index:
                provincia = self.procesar_provincia(row['Provincia Residencia'])
            if 'id_canton' in row.index:
                canton = self.procesar_canton(row['id_canton'], provincia)
            if 'id_didistrito' in row.index:
                distrito = self.procesar_distrito(row['id_didistrito'], canton)
            if 'Direccion exacta' in row.index:
                direccion = str(row['Direccion exacta']).strip() if not pd.isna(row['Direccion exacta']) else ''

            # Procesar información de contacto (columnas opcionales)
            telefono = ''
            telefono_casa = ''
            correo = ''
            
            if 'Telefono estudiante' in row.index:
                telefono = str(row['Telefono estudiante']).strip() if not pd.isna(row['Telefono estudiante']) else ''
            if 'Telefono casa' in row.index:
                telefono_casa = str(row['Telefono casa']).strip() if not pd.isna(row['Telefono casa']) else ''
            if 'Correo electronico' in row.index:
                correo = str(row['Correo electronico']).strip() if not pd.isna(row['Correo electronico']) else ''

            return {
                'cedula': cedula,
                'primer_apellido': primer_apellido,
                'segundo_apellido': segundo_apellido,
                'nombre': nombre,
                'fecha_nacimiento': fecha_nac,
                'genero': genero,
                'nacionalidad': nacionalidad,
                'provincia': provincia,
                'canton': canton,
                'distrito': distrito,
                'direccion': direccion,
                'telefono': telefono,
                'telefono_casa': telefono_casa,
                'correo': correo,
                'institucion': institucion,
                'tipo_identificacion': tipo_identificacion
            }

        except Exception as e:
            raise ValueError(f"Error procesando fila: {str(e)}")

    def validar_cedula(self, cedula):
        """Validar formato de cédula costarricense"""
        # Remover espacios y guiones
        cedula = re.sub(r'[\s-]', '', cedula)
        # Debe tener 9 dígitos
        return len(cedula) == 9 and cedula.isdigit()

    def procesar_fecha(self, fecha):
        """Procesar fecha de nacimiento"""
        if pd.isna(fecha):
            return None
        
        try:
            if isinstance(fecha, str):
                # Intentar diferentes formatos
                for formato in ['%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d']:
                    try:
                        return datetime.strptime(fecha, formato).date()
                    except ValueError:
                        continue
            elif hasattr(fecha, 'date'):
                return fecha.date()
            
            raise ValueError(f"Formato de fecha no reconocido: {fecha}")
        except Exception:
            raise ValueError(f"Fecha inválida: {fecha}")

    def procesar_genero(self, genero):
        """Procesar y estandarizar género"""
        if pd.isna(genero):
            return None
        
        genero_str = str(genero).strip().lower()
        
        # Buscar o crear sexo
        try:
            if genero_str in ['m', 'masculino', 'male']:
                return Sexo.objects.get(nombre__icontains='Masculino')
            elif genero_str in ['f', 'femenino', 'female']:
                return Sexo.objects.get(nombre__icontains='Femenino')
            else:
                # Intentar buscar por nombre exacto
                return Sexo.objects.get(nombre__icontains=genero_str)
        except Sexo.DoesNotExist:
            # Crear nuevo sexo si no existe
            if genero_str in ['m', 'masculino', 'male']:
                return Sexo.objects.create(nombre='Masculino')
            elif genero_str in ['f', 'femenino', 'female']:
                return Sexo.objects.create(nombre='Femenino')
            else:
                return Sexo.objects.create(nombre=genero_str.title())

    def procesar_nacionalidad(self, nacionalidad):
        """Procesar nacionalidad"""
        if pd.isna(nacionalidad):
            return None
        
        nacionalidad_str = str(nacionalidad).strip()
        
        # Buscar o crear nacionalidad
        try:
            return Nacionalidad.objects.get(nombre__icontains=nacionalidad_str)
        except Nacionalidad.DoesNotExist:
            # Crear nueva nacionalidad si no existe
            return Nacionalidad.objects.create(nombre=nacionalidad_str)

    def procesar_provincia(self, provincia):
        """Procesar provincia"""
        if pd.isna(provincia):
            return None
        
        provincia_str = str(provincia).strip()
        
        # Buscar o crear provincia
        try:
            return Provincia.objects.get(nombre__icontains=provincia_str)
        except Provincia.DoesNotExist:
            # Crear nueva provincia si no existe
            return Provincia.objects.create(nombre=provincia_str)

    def procesar_canton(self, canton, provincia):
        """Procesar cantón"""
        if pd.isna(canton) or not provincia:
            return None
        
        canton_str = str(canton).strip()
        
        # Buscar o crear cantón
        try:
            return Canton.objects.get(nombre__icontains=canton_str, provincia=provincia)
        except Canton.DoesNotExist:
            # Crear nuevo cantón si no existe
            return Canton.objects.create(nombre=canton_str, provincia=provincia)

    def procesar_distrito(self, distrito, canton):
        """Procesar distrito"""
        if pd.isna(distrito) or not canton:
            return None
        
        distrito_str = str(distrito).strip()
        
        # Buscar o crear distrito
        try:
            return Distrito.objects.get(nombre__icontains=distrito_str, canton=canton)
        except Distrito.DoesNotExist:
            # Crear nuevo distrito si no existe
            return Distrito.objects.create(nombre=distrito_str, canton=canton)

    def procesar_tipo_identificacion(self, tipo):
        """Procesar tipo de identificación"""
        if pd.isna(tipo):
            tipo = 'Cédula'
        
        tipo_str = str(tipo).strip()
        
        # Buscar o crear tipo de identificación
        try:
            return TipoIdentificacion.objects.get(nombre__icontains=tipo_str)
        except TipoIdentificacion.DoesNotExist:
            # Crear nuevo tipo si no existe
            return TipoIdentificacion.objects.create(nombre=tipo_str)

    @transaction.atomic
    def crear_estudiante(self, data):
        """Crear nuevo estudiante"""
        Estudiante.objects.create(
            identificacion=data['cedula'],
            primer_apellido=data['primer_apellido'],
            segundo_apellido=data['segundo_apellido'],
            nombres=data['nombre'],
            fecha_nacimiento=data['fecha_nacimiento'],
            sexo=data['genero'],
            nacionalidad=data['nacionalidad'],
            provincia=data['provincia'],
            canton=data['canton'],
            distrito=data['distrito'],
            direccion_exacta=data['direccion'],
            celular=data['telefono'],
            telefono_casa=data['telefono_casa'],
            correo=data['correo'],
            institucion=data['institucion'],
            tipo_identificacion=data['tipo_identificacion']
        )

    @transaction.atomic
    def actualizar_estudiante(self, data):
        """Actualizar estudiante existente"""
        estudiante = Estudiante.objects.get(identificacion=data['cedula'])
        estudiante.primer_apellido = data['primer_apellido']
        estudiante.segundo_apellido = data['segundo_apellido']
        estudiante.nombres = data['nombre']
        estudiante.fecha_nacimiento = data['fecha_nacimiento']
        estudiante.sexo = data['genero']
        estudiante.nacionalidad = data['nacionalidad']
        estudiante.provincia = data['provincia']
        estudiante.canton = data['canton']
        estudiante.distrito = data['distrito']
        estudiante.direccion_exacta = data['direccion']
        estudiante.celular = data['telefono']
        estudiante.telefono_casa = data['telefono_casa']
        estudiante.correo = data['correo']
        estudiante.institucion = data['institucion']
        estudiante.tipo_identificacion = data['tipo_identificacion']
        estudiante.save()

    def mostrar_resultados(self, resultados, dry_run):
        """Mostrar resumen de la importación"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("RESUMEN DE IMPORTACIÓN")
        self.stdout.write("="*50)
        
        if dry_run:
            self.stdout.write("🔍 MODO SIMULACIÓN - No se guardaron datos")
        
        self.stdout.write(f"📊 Total de filas procesadas: {resultados['total']}")
        self.stdout.write(f"✅ Filas válidas: {resultados['validos']}")
        self.stdout.write(f"❌ Errores encontrados: {len(resultados['errores'])}")
        self.stdout.write(f"🔄 Estudiantes duplicados: {resultados['duplicados']}")
        
        if not dry_run:
            self.stdout.write(f"🆕 Estudiantes creados: {resultados['creados']}")
            self.stdout.write(f"📝 Estudiantes actualizados: {resultados['actualizados']}")
        
        if resultados['errores']:
            self.stdout.write("\n❌ ERRORES ENCONTRADOS:")
            for error in resultados['errores'][:10]:  # Mostrar solo los primeros 10
                self.stdout.write(f"  - {error}")
            if len(resultados['errores']) > 10:
                self.stdout.write(f"  ... y {len(resultados['errores']) - 10} errores más")
        
        self.stdout.write("\n" + "="*50)
