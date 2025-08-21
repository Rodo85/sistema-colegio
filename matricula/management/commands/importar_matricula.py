from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
import pandas as pd
import re
from datetime import datetime
import logging

# Importar modelos
from matricula.models import Estudiante, PersonaContacto, EncargadoEstudiante, MatriculaAcademica
from catalogos.models import Nacionalidad, Sexo, Parentesco, Escolaridad, Ocupacion, Provincia, Canton, Distrito, TipoIdentificacion, Nivel, Seccion, Subgrupo, Especialidad, CursoLectivo
from core.models import Institucion

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Importar estudiantes masivamente desde archivo Excel/CSV'
    
    def add_arguments(self, parser):
        parser.add_argument('archivo', type=str, help='Ruta al archivo Excel/CSV')
        parser.add_argument('--institucion-id', type=int, default=1, help='ID de la institución (default: 1)')
        parser.add_argument('--dry-run', action='store_true', help='Ejecutar sin guardar en base de datos')
        parser.add_argument('--verbose', action='store_true', help='Mostrar información detallada')
    
    def handle(self, *args, **options):
        archivo = options['archivo']
        institucion_id = options['institucion_id']
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        if verbose:
            self.stdout.write(f"🚀 Iniciando importación desde: {archivo}")
            self.stdout.write(f"🏢 Institución ID: {institucion_id}")
            self.stdout.write(f"🧪 Modo dry-run: {'SÍ' if dry_run else 'NO'}")
        
        try:
            # Leer archivo
            df = self.leer_archivo(archivo)
            if verbose:
                self.stdout.write(f"📊 Archivo leído: {len(df)} filas")
            
            # Validar estructura
            self.validar_estructura(df)
            if verbose:
                self.stdout.write("✅ Estructura del archivo validada")
            
            # Obtener institución
            institucion = Institucion.objects.get(id=institucion_id)
            if verbose:
                self.stdout.write(f"🏢 Institución: {institucion.nombre}")
            
            # Procesar filas
            resultados = {
                'estudiantes_creados': 0,
                'estudiantes_actualizados': 0,
                'encargados_creados': 0,
                'encargados_actualizados': 0,
                'matriculas_creadas': 0,
                'matriculas_actualizadas': 0,
                'errores': [],
                'advertencias': []
            }
            
            for index, row in df.iterrows():
                try:
                    if verbose:
                        self.stdout.write(f"📝 Procesando fila {index + 1}: {row.get('identificacion', 'N/A')}")
                    
                    self.procesar_fila_completa(row, institucion, dry_run, resultados, verbose)
                    
                except Exception as e:
                    error_msg = f"Fila {index + 1}: {str(e)}"
                    resultados['errores'].append(error_msg)
                    if verbose:
                        self.stdout.write(f"❌ {error_msg}")
            
            # Mostrar resultados
            self.mostrar_resultados(resultados, verbose)
            
        except Exception as e:
            raise CommandError(f"Error durante la importación: {str(e)}")
    
    def leer_archivo(self, archivo):
        """Leer archivo Excel o CSV"""
        try:
            if archivo.endswith('.csv'):
                df = pd.read_csv(archivo, sep=';', encoding='utf-8')
            else:
                df = pd.read_excel(archivo)
            
            # Limpiar datos
            df = df.replace({pd.NA: None, '': None, 'nan': None, 'NaN': None})
            
            # Limpiar nombres de columnas
            df.columns = df.columns.str.strip()
            
            return df
        except Exception as e:
            raise CommandError(f"Error al leer archivo: {str(e)}")
    
    def validar_estructura(self, df):
        """Validar que el archivo tenga las columnas requeridas"""
        columnas_requeridas = [
            'tipo_estudiante', 'tipo_identificacion', 'identificacion',
            '1er apellido estudiante', '2do apellido estudiante', 'Nombre estudiante2',
            'Fecha nacimiento', 'id_Genero', 'id_nacionalidad'
        ]
        
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            raise CommandError(f"Columnas faltantes: {', '.join(columnas_faltantes)}")
    
    @transaction.atomic
    def procesar_fila_completa(self, row, institucion, dry_run, resultados, verbose):
        """Procesar una fila completa del archivo"""
        
        # Procesar estudiante
        estudiante = self.procesar_estudiante(row, institucion, dry_run, resultados, verbose)
        
        # Procesar encargado
        encargado = self.procesar_encargado(row, dry_run, resultados, verbose)
        
        # Vincular encargado con estudiante
        if estudiante and encargado:
            self.vincular_encargado_estudiante(estudiante, encargado, row, dry_run, resultados, verbose)
        
        # Procesar matrícula académica
        if estudiante:
            self.procesar_matricula_academica(estudiante, row, institucion, dry_run, resultados, verbose)
    
    def procesar_estudiante(self, row, institucion, dry_run, resultados, verbose):
        """Procesar estudiante"""
        try:
            identificacion = str(row['identificacion']).strip()
            if not identificacion or identificacion == 'None':
                return None
            
            # Procesar datos básicos
            tipo_identificacion = self.procesar_tipo_identificacion(row.get('tipo_identificacion'), dry_run)
            sexo = self.procesar_sexo(row.get('id_Genero'), dry_run)
            nacionalidad = self.procesar_nacionalidad(row.get('id_nacionalidad'), dry_run)
            provincia = self.procesar_provincia(row.get('id_provincia'), dry_run)
            canton = self.procesar_canton(row.get('id_canton'), provincia, dry_run)
            distrito = self.procesar_distrito(row.get('id_didistrito'), canton, dry_run)
            
            # Datos del estudiante
            datos_estudiante = {
                'identificacion': identificacion,
                'tipo_identificacion': tipo_identificacion,
                'primer_apellido': str(row.get('1er apellido estudiante', '')).strip().upper(),
                'segundo_apellido': str(row.get('2do apellido estudiante', '')).strip().upper(),
                'nombres': str(row.get('Nombre estudiante2', '')).strip().upper(),
                'fecha_nacimiento': self.procesar_fecha(row.get('Fecha nacimiento')),
                'telefono': str(row.get('Telefono estudiante', '')).strip() if pd.notna(row.get('Telefono estudiante')) else None,
                'sexo': sexo,
                'nacionalidad': nacionalidad,
                'provincia': provincia,
                'canton': canton,
                'distrito': distrito,
                'direccion_exacta': str(row.get('Direccion exacta', '')).strip() if pd.notna(row.get('Direccion exacta')) else None,
                'institucion': institucion
            }
            
            # Crear o actualizar estudiante
            if dry_run:
                if verbose:
                    self.stdout.write(f"🧪 DRY-RUN: Estudiante {identificacion} sería {'creado' if not Estudiante.objects.filter(identificacion=identificacion).exists() else 'actualizado'}")
                return None
            else:
                estudiante, created = Estudiante.objects.update_or_create(
                    identificacion=identificacion,
                    defaults=datos_estudiante
                )
                
                if created:
                    resultados['estudiantes_creados'] += 1
                    if verbose:
                        self.stdout.write(f"✅ Estudiante creado: {identificacion}")
                else:
                    resultados['estudiantes_actualizados'] += 1
                    if verbose:
                        self.stdout.write(f"🔄 Estudiante actualizado: {identificacion}")
                
                return estudiante
                
        except Exception as e:
            resultados['errores'].append(f"Error procesando estudiante {row.get('identificacion', 'N/A')}: {str(e)}")
            return None
    
    def procesar_encargado(self, row, dry_run, resultados, verbose):
        """Procesar encargado del estudiante"""
        try:
            cedula_encargado = str(row.get('cedula encargado', '')).strip()
            if not cedula_encargado or cedula_encargado == 'None':
                return None
            
            # Procesar datos del encargado
            parentesco = self.procesar_parentesco(row.get('Parentesco'), dry_run)
            escolaridad = self.procesar_escolaridad(row.get('Escolaridad'), dry_run)
            ocupacion = self.procesar_ocupacion(row.get('Ocupacion'), dry_run)
            
            # Datos del encargado
            datos_encargado = {
                'identificacion': cedula_encargado,
                'nombres': str(row.get('Nombre encargado', '')).strip().upper(),
                'parentesco': parentesco,
                'telefono': str(row.get('Teléfono encargado', '')).strip() if pd.notna(row.get('Teléfono encargado')) else None,
                'correo_electronico': str(row.get('Correo electronico', '')).strip() if pd.notna(row.get('Correo electronico')) else None,
                'lugar_trabajo': str(row.get('Lugar de trabajo', '')).strip() if pd.notna(row.get('Lugar de trabajo')) else None,
                'telefono_trabajo': str(row.get('Telefono del trabajo', '')).strip() if pd.notna(row.get('Telefono del trabajo')) else None,
                'escolaridad': escolaridad,
                'ocupacion': ocupacion
            }
            
            # Crear o actualizar encargado
            if dry_run:
                if verbose:
                    self.stdout.write(f"🧪 DRY-RUN: Encargado {cedula_encargado} sería {'creado' if not PersonaContacto.objects.filter(identificacion=cedula_encargado).exists() else 'actualizado'}")
                return None
            else:
                encargado, created = PersonaContacto.objects.update_or_create(
                    identificacion=cedula_encargado,
                    defaults=datos_encargado
                )
                
                if created:
                    resultados['encargados_creados'] += 1
                    if verbose:
                        self.stdout.write(f"✅ Encargado creado: {cedula_encargado}")
                else:
                    resultados['encargados_actualizados'] += 1
                    if verbose:
                        self.stdout.write(f"🔄 Encargado actualizado: {cedula_encargado}")
                
                return encargado
                
        except Exception as e:
            resultados['errores'].append(f"Error procesando encargado {row.get('cedula encargado', 'N/A')}: {str(e)}")
            return None
    
    def vincular_encargado_estudiante(self, estudiante, encargado, row, dry_run, resultados, verbose):
        """Vincular encargado con estudiante"""
        try:
            vive_con_estudiante = str(row.get('Vive con el estudiante', '')).strip().upper() == 'SI'
            
            datos_vinculo = {
                'estudiante': estudiante,
                'persona_contacto': encargado,
                'vive_con_estudiante': vive_con_estudiante
            }
            
            if dry_run:
                if verbose:
                    self.stdout.write(f"🧪 DRY-RUN: Vinculo encargado-estudiante sería creado")
                return
            else:
                vinculo, created = EncargadoEstudiante.objects.get_or_create(
                    estudiante=estudiante,
                    persona_contacto=encargado,
                    defaults=datos_vinculo
                )
                
                if created:
                    if verbose:
                        self.stdout.write(f"✅ Vinculo encargado-estudiante creado")
                else:
                    # Actualizar si ya existe
                    vinculo.vive_con_estudiante = vive_con_estudiante
                    vinculo.save()
                    if verbose:
                        self.stdout.write(f"🔄 Vinculo encargado-estudiante actualizado")
                
        except Exception as e:
            resultados['errores'].append(f"Error vinculando encargado-estudiante: {str(e)}")
    
    def procesar_matricula_academica(self, estudiante, row, institucion, dry_run, resultados, verbose):
        """Procesar matrícula académica del estudiante"""
        try:
            # Extraer nivel y sección
            nivel = self.extraer_nivel(row.get('Nivel que Matricula'))
            seccion = self.extraer_seccion(row.get('Sección'))
            subgrupo = self.extraer_subgrupo(row.get('subgrupp'), seccion)
            especialidad = self.procesar_especialidad(row.get('Especialidad'), dry_run)
            
            if not nivel:
                resultados['advertencias'].append(f"Nivel no válido para estudiante {estudiante.identificacion}")
                return
            
            # Buscar curso lectivo activo
            curso_lectivo = CursoLectivo.objects.filter(activo=True).first()
            if not curso_lectivo:
                resultados['advertencias'].append(f"No hay curso lectivo activo")
                return
            
            # Buscar nivel en catálogos
            try:
                nivel_obj = Nivel.objects.get(numero=nivel)
            except Nivel.DoesNotExist:
                resultados['advertencias'].append(f"Nivel {nivel} no encontrado en catálogos")
                return
            
            # Buscar sección
            seccion_obj = None
            if seccion:
                try:
                    seccion_obj = Seccion.objects.get(numero=seccion, nivel=nivel_obj)
                except Seccion.DoesNotExist:
                    resultados['advertencias'].append(f"Sección {seccion} del nivel {nivel} no encontrada")
            
            # Buscar subgrupo
            subgrupo_obj = None
            if subgrupo and seccion_obj:
                try:
                    subgrupo_obj = Subgrupo.objects.get(letra=subgrupo, seccion=seccion_obj)
                except Subgrupo.DoesNotExist:
                    resultados['advertencias'].append(f"Subgrupo {subgrupo} de la sección {seccion} no encontrado")
            
            # Datos de la matrícula
            datos_matricula = {
                'estudiante': estudiante,
                'nivel': nivel_obj,
                'seccion': seccion_obj,
                'subgrupo': subgrupo_obj,
                'curso_lectivo': curso_lectivo,
                'especialidad': especialidad,
                'estado': 'activo'
            }
            
            # Crear o actualizar matrícula
            if dry_run:
                if verbose:
                    self.stdout.write(f"🧪 DRY-RUN: Matrícula académica sería {'creada' if not MatriculaAcademica.objects.filter(estudiante=estudiante, curso_lectivo=curso_lectivo).exists() else 'actualizada'}")
                return
            else:
                matricula, created = MatriculaAcademica.objects.update_or_create(
                    estudiante=estudiante,
                    curso_lectivo=curso_lectivo,
                    defaults=datos_matricula
                )
                
                if created:
                    resultados['matriculas_creadas'] += 1
                    if verbose:
                        self.stdout.write(f"✅ Matrícula académica creada para estudiante {estudiante.identificacion}")
                else:
                    resultados['matriculas_actualizadas'] += 1
                    if verbose:
                        self.stdout.write(f"🔄 Matrícula académica actualizada para estudiante {estudiante.identificacion}")
                
        except Exception as e:
            resultados['errores'].append(f"Error procesando matrícula académica: {str(e)}")
    
    # Métodos auxiliares para procesar catálogos
    def procesar_tipo_identificacion(self, valor, dry_run):
        if not valor:
            return TipoIdentificacion.objects.get(nombre__icontains='cédula')
        
        mapeo = {
            '1': 'cédula',
            '2': 'dimex',
            '3': 'pasaporte'
        }
        
        nombre = mapeo.get(str(valor), 'cédula')
        return TipoIdentificacion.objects.get(nombre__icontains=nombre)
    
    def procesar_sexo(self, valor, dry_run):
        if not valor:
            return Sexo.objects.get(nombre__icontains='masculino')
        
        mapeo = {
            '1': 'femenino',
            '2': 'masculino'
        }
        
        nombre = mapeo.get(str(valor), 'masculino')
        return Sexo.objects.get(nombre__icontains=nombre)
    
    def procesar_nacionalidad(self, valor, dry_run):
        if not valor:
            return Nacionalidad.objects.get(nombre__icontains='costarricense')
        
        mapeo = {
            '1': 'costarricense',
            '2': 'extranjero'
        }
        
        nombre = mapeo.get(str(valor), 'costarricense')
        return Nacionalidad.objects.get(nombre__icontains=nombre)
    
    def procesar_provincia(self, valor, dry_run):
        if not valor:
            return Provincia.objects.first()
        
        try:
            return Provincia.objects.get(id=valor)
        except Provincia.DoesNotExist:
            return Provincia.objects.first()
    
    def procesar_canton(self, valor, provincia, dry_run):
        if not valor or not provincia:
            return None
        
        try:
            return Canton.objects.get(id=valor, provincia=provincia)
        except Canton.DoesNotExist:
            return None
    
    def procesar_distrito(self, valor, canton, dry_run):
        if not valor or not canton:
            return None
        
        try:
            return Distrito.objects.get(id=valor, canton=canton)
        except Distrito.DoesNotExist:
            return None
    
    def procesar_parentesco(self, valor, dry_run):
        if not valor:
            return Parentesco.objects.get(nombre__icontains='madre')
        
        return Parentesco.objects.get(nombre__icontains=valor)
    
    def procesar_escolaridad(self, valor, dry_run):
        if not valor:
            return Escolaridad.objects.get(nombre__icontains='secundaria')
        
        return Escolaridad.objects.get(nombre__icontains=valor)
    
    def procesar_ocupacion(self, valor, dry_run):
        if not valor:
            return Ocupacion.objects.get(nombre__icontains='ama de casa')
        
        return Ocupacion.objects.get(nombre__icontains=valor)
    
    def procesar_especialidad(self, valor, dry_run):
        if not valor:
            return None
        
        try:
            return Especialidad.objects.get(nombre__icontains=valor)
        except Especialidad.DoesNotExist:
            return None
    
    def extraer_nivel(self, valor):
        if not valor:
            return None
        
        # Buscar número en el texto (ej: "8 (Octavo)" -> 8)
        match = re.search(r'(\d+)', str(valor))
        if match:
            return int(match.group(1))
        return None
    
    def extraer_seccion(self, valor):
        if not valor:
            return None
        
        # Buscar formato como "8-5" o "7-1"
        match = re.search(r'(\d+)-(\d+)', str(valor))
        if match:
            return f"{match.group(1)}-{match.group(2)}"
        return None
    
    def extraer_subgrupo(self, valor, seccion):
        if not valor:
            return None
        
        # Limpiar y validar subgrupo
        subgrupo = str(valor).strip().upper()
        if subgrupo in ['A', 'B', 'C', 'D', 'E', 'F']:
            return subgrupo
        return None
    
    def procesar_fecha(self, valor):
        if not valor or pd.isna(valor):
            return None
        
        try:
            # Intentar diferentes formatos de fecha
            for formato in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                try:
                    return datetime.strptime(str(valor), formato).date()
                except ValueError:
                    continue
            
            # Si no funciona, devolver None
            return None
        except:
            return None
    
    def mostrar_resultados(self, resultados, verbose):
        """Mostrar resumen de resultados"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("📊 RESUMEN DE IMPORTACIÓN")
        self.stdout.write("="*60)
        
        self.stdout.write(f"✅ Estudiantes creados: {resultados['estudiantes_creados']}")
        self.stdout.write(f"🔄 Estudiantes actualizados: {resultados['estudiantes_actualizados']}")
        self.stdout.write(f"✅ Encargados creados: {resultados['encargados_creados']}")
        self.stdout.write(f"🔄 Encargados actualizados: {resultados['encargados_actualizados']}")
        self.stdout.write(f"✅ Matrículas creadas: {resultados['matriculas_creadas']}")
        self.stdout.write(f"🔄 Matrículas actualizadas: {resultados['matriculas_actualizadas']}")
        
        if resultados['errores']:
            self.stdout.write(f"\n❌ Errores ({len(resultados['errores'])}):")
            for error in resultados['errores']:
                self.stdout.write(f"   • {error}")
        
        if resultados['advertencias']:
            self.stdout.write(f"\n⚠️ Advertencias ({len(resultados['advertencias'])}):")
            for advertencia in resultados['advertencias']:
                self.stdout.write(f"   • {advertencia}")
        
        self.stdout.write("\n" + "="*60)
