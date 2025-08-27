from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import pandas as pd
from datetime import datetime
import re
from django.utils import timezone

from matricula.models import Estudiante, PersonaContacto, EncargadoEstudiante, MatriculaAcademica
from catalogos.models import (
    Nacionalidad, Sexo, Parentesco, Escolaridad, Ocupacion, 
    Provincia, Canton, Distrito, TipoIdentificacion, Nivel, 
    Seccion, Subgrupo, Especialidad, Adecuacion, EstadoCivil
)
from core.models import Institucion
from config_institucional.models import CursoLectivo

class Command(BaseCommand):
    help = 'Importar estudiantes desde el archivo CSV específico del colegio'

    def add_arguments(self, parser):
        parser.add_argument('archivo_csv', type=str, help='Ruta al archivo CSV')
        parser.add_argument('--curso-lectivo', type=int, help='ID del curso lectivo')
        parser.add_argument('--dry-run', action='store_true', help='Solo validar, no guardar')

    def handle(self, *args, **options):
        """Maneja la importación de estudiantes desde CSV"""
        archivo_csv = options['archivo_csv']
        curso_lectivo_id = options.get('curso_lectivo')
        dry_run = options['dry_run']
        
        try:
            # Leer el archivo CSV
            self.stdout.write(f"📖 Leyendo archivo: {archivo_csv}")
            df = pd.read_csv(archivo_csv, sep=';', encoding='utf-8')
            
            # Validar columnas
            self.validar_columnas(df)
            
            # Obtener curso lectivo
            curso_lectivo = self.obtener_curso_lectivo(curso_lectivo_id)
            self.stdout.write(f"📚 Usando curso lectivo: {curso_lectivo.nombre}")
            
            # Procesar datos
            resultados = self.procesar_estudiantes(df, curso_lectivo, dry_run)
            
            # Mostrar resultados
            self.mostrar_resultados(resultados, dry_run)
            
        except Exception as e:
            raise CommandError(f"Error al procesar el archivo: {str(e)}")

    def validar_columnas(self, df):
        """Valida que el CSV tenga las columnas requeridas"""
        columnas_requeridas = [
            'institucion_id', 'tipo_estudiante', 'tipo_identificacion_id', 'identificacion',
            'primer_apellido', 'segundo_apellido', 'nombres', 'fecha_nacimiento', 'celular',
            'sexo_id', 'nacionalidad_id', 'telefono_casa', 'provincia_id', 'canton_id', 'distrito_id',
            'direccion_exacta', 'foto', 'correo', 'adecuacion_id', 'numero_poliza', 'rige_poliza',
            'vence_poliza', 'ed_religiosa', 'presenta_enfermedad', 'detalle_enfermedad',
            'medicamentos_consume', 'autoriza_derecho_imagen', 'subgrupp', 'Sección', 'Nivel que Matricula',
            'Especialidad ', 'identificacion_contacto', 'primer_apellido_contacto', 'segundo_apellido_contacto',
            'nombres_contacto', 'principal_contacto', 'estado_civil_id_contacto', 'id_Parentesco_contacto',
            'celular_avisos_contacto', 'correo_contacto', 'Vive con el estudiante_contacto',
            'lugar_trabajo_contacto', 'telefono_trabajo_contacto', 'id_Escolaridad_contacto', 'ocupacion_id_contacto'
        ]
        
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            raise ValueError(f"Columnas faltantes: {', '.join(columnas_faltantes)}")
        
        self.stdout.write("✅ Todas las columnas requeridas están presentes")
        return True

    def obtener_curso_lectivo(self, curso_lectivo_id=None):
        """Obtiene el curso lectivo especificado o el más reciente activo"""
        if curso_lectivo_id:
            try:
                return CursoLectivo.objects.get(id=curso_lectivo_id)
            except CursoLectivo.DoesNotExist:
                raise ValueError(f"No se encontró el curso lectivo con ID: {curso_lectivo_id}")
        
        # Si no se especifica, usar el más reciente activo
        curso_lectivo = CursoLectivo.objects.filter(activo=True).order_by('-anio').first()
        if not curso_lectivo:
            raise ValueError("No hay cursos lectivos activos disponibles")
        
        return curso_lectivo

    def procesar_estudiantes(self, df, curso_lectivo, dry_run):
        """Procesa todos los estudiantes del DataFrame"""
        resultados = {
            'validos': 0,
            'creados': 0,
            'actualizados': 0,
            'errores': 0,
            'encargados_creados': 0,
            'matriculas_creadas': 0
        }
        
        for index, row in df.iterrows():
            try:
                # Validar y procesar fila
                estudiante_data = self.procesar_fila(row, curso_lectivo)
                
                if not estudiante_data:
                    resultados['errores'] += 1
                    continue
                
                # Verificar si el estudiante ya existe
                if Estudiante.objects.filter(identificacion=estudiante_data['identificacion']).exists():
                    if not dry_run:
                        # Actualizar estudiante existente
                        estudiante = Estudiante.objects.get(identificacion=estudiante_data['identificacion'])
                        self.actualizar_estudiante(estudiante, estudiante_data)
                        resultados['actualizados'] += 1
                    resultados['validos'] += 1
                else:
                    if not dry_run:
                        # Crear nuevo estudiante
                        self.crear_estudiante(estudiante_data)
                        resultados['creados'] += 1
                    resultados['validos'] += 1
                
                # Procesar encargado
                if not dry_run and estudiante_data.get('encargado_data'):
                    encargado = self.procesar_encargado(estudiante_data['estudiante'], estudiante_data['encargado_data'], row)
                    if encargado:
                        resultados['encargados_creados'] += 1
                
                # Procesar matrícula
                if not dry_run and estudiante_data.get('matricula_data'):
                    matricula = self.procesar_matricula(estudiante_data['estudiante'], estudiante_data['matricula_data'])
                    if matricula:
                        resultados['matriculas_creadas'] += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error en fila {index + 1}: {str(e)}")
                )
                resultados['errores'] += 1
        
        return resultados

    def obtener_institucion(self, institucion_id=None):
        """Obtiene la institución especificada o la primera disponible"""
        if institucion_id:
            try:
                return Institucion.objects.get(id=institucion_id)
            except Institucion.DoesNotExist:
                raise ValueError(f"No se encontró la institución con ID: {institucion_id}")
        
        # Si no se especifica, usar la primera institución disponible
        institucion = Institucion.objects.first()
        if not institucion:
            raise ValueError("No hay instituciones disponibles")
        
        return institucion

    def procesar_fila(self, row, curso_lectivo):
        """Procesa una fila del CSV y retorna los datos del estudiante"""
        try:
            # Validar identificación
            identificacion = str(row['identificacion']).strip()
            if not self.validar_identificacion(identificacion):
                raise ValueError("Identificación es obligatoria y no puede estar vacía")
            
            # Obtener institución del CSV o usar una por defecto
            institucion_id = int(row['institucion_id']) if not pd.isna(row['institucion_id']) else None
            institucion = self.obtener_institucion(institucion_id)
            
            # Procesar datos básicos del estudiante
            fecha_nac = self.procesar_fecha(row['fecha_nacimiento'])
            if pd.isna(fecha_nac):
                fecha_nac = timezone.now().date()
            
            # Procesar datos del encargado
            encargado_data = self.procesar_datos_encargado(row)
            
            # Procesar datos de matrícula
            matricula_data = self.procesar_datos_matricula(row, curso_lectivo, institucion)
            
            tipo_estudiante_str = str(row['tipo_estudiante']).strip().upper() if not pd.isna(row['tipo_estudiante']) else 'PR'
            es_plan_nacional = tipo_estudiante_str in ['PN', 'PE', 'PLAN NACIONAL', 'PLAN NACION']
            
            estudiante_data = {
                'identificacion': identificacion,
                'tipo_estudiante': tipo_estudiante_str if tipo_estudiante_str in ['PR', 'PN'] else ('PN' if es_plan_nacional else 'PR'),
                'nombres': str(row['nombres']).strip().upper(),
                'primer_apellido': str(row['primer_apellido']).strip().upper(),
                'segundo_apellido': str(row['segundo_apellido']).strip().upper() if not pd.isna(row['segundo_apellido']) else '',
                'fecha_nacimiento': fecha_nac,
                'celular': str(row['celular']).strip() if not pd.isna(row['celular']) else '',
                'sexo': self.procesar_genero(row['sexo_id']),
                'nacionalidad': self.procesar_nacionalidad(row['nacionalidad_id']),
                'tipo_identificacion': self.procesar_tipo_identificacion(row['tipo_identificacion_id']),
                'provincia': self.procesar_provincia(row['provincia_id']),
                'canton': self.procesar_canton(row['canton_id']),
                'distrito': self.procesar_distrito(row['distrito_id']),
                'direccion_exacta': str(row['direccion_exacta']).strip().upper() if not pd.isna(row['direccion_exacta']) else '',
                'foto': str(row['foto']).strip() if not pd.isna(row['foto']) else '',
                'correo': str(row['correo']).strip().lower() if not pd.isna(row['correo']) else '',
                'adecuacion': self.procesar_adecuacion(row['adecuacion_id']),
                'numero_poliza': str(row['numero_poliza']).strip() if not pd.isna(row['numero_poliza']) else '',
                'rige_poliza': self.procesar_fecha(row['rige_poliza']) if not pd.isna(row['rige_poliza']) else None,
                'vence_poliza': self.procesar_fecha(row['vence_poliza']) if not pd.isna(row['vence_poliza']) else None,
                'ed_religiosa': str(row['ed_religiosa']).lower() == 'true' if not pd.isna(row['ed_religiosa']) else False,
                'presenta_enfermedad': str(row['presenta_enfermedad']).lower() == 'true' if not pd.isna(row['presenta_enfermedad']) else False,
                'detalle_enfermedad': str(row['detalle_enfermedad']).strip().upper() if not pd.isna(row['detalle_enfermedad']) else '',
                'medicamentos_consume': str(row['medicamentos_consume']).strip().upper() if not pd.isna(row['medicamentos_consume']) else '',
                'autoriza_derecho_imagen': str(row['autoriza_derecho_imagen']).lower() == 'true' if not pd.isna(row['autoriza_derecho_imagen']) else False,
                'institucion': institucion,
                'encargado_data': encargado_data,
                'matricula_data': matricula_data
            }
            
            return estudiante_data
            
        except Exception as e:
            raise ValueError(f"Error procesando fila: {str(e)}")

    def procesar_datos_encargado(self, row):
        """Procesa los datos del encargado desde la fila del CSV"""
        try:
            # Validar identificación del encargado
            identificacion_encargado = str(row['identificacion_contacto']).strip()
            if not self.validar_identificacion(identificacion_encargado):
                raise ValueError("Identificación del encargado es obligatoria")
            
            return {
                'identificacion': identificacion_encargado,
                'nombre': str(row['nombres_contacto']).strip().upper(),
                'apellido1': str(row['primer_apellido_contacto']).strip().upper(),
                'apellido2': str(row['segundo_apellido_contacto']).strip().upper() if not pd.isna(row['segundo_apellido_contacto']) else '',
                'fecha_nacimiento': timezone.now().date(),  # No hay fecha de nacimiento del encargado en el CSV
                'genero': self.procesar_genero(row['sexo_id']),  # Usar el mismo género del estudiante
                'nacionalidad': self.procesar_nacionalidad(row['nacionalidad_id']),  # Usar la misma nacionalidad del estudiante
                'tipo_identificacion': self.procesar_tipo_identificacion(row['tipo_identificacion_id']),  # Usar el mismo tipo del estudiante
                'parentesco': self.procesar_parentesco(row['id_Parentesco_contacto']),
                'provincia': self.procesar_provincia(row['provincia_id']),  # Usar la misma provincia del estudiante
                'canton': self.procesar_canton(row['canton_id']),  # Usar el mismo cantón del estudiante
                'distrito': self.procesar_distrito(row['distrito_id']),  # Usar el mismo distrito del estudiante
                'direccion_exacta': str(row['lugar_trabajo_contacto']).strip().upper() if not pd.isna(row['lugar_trabajo_contacto']) else '',
                'celular': str(row['celular_avisos_contacto']).strip() if not pd.isna(row['celular_avisos_contacto']) else '',
                'telefono_casa': str(row['telefono_trabajo_contacto']).strip() if not pd.isna(row['telefono_trabajo_contacto']) else '',
                'correo': str(row['correo_contacto']).strip().lower() if not pd.isna(row['correo_contacto']) else '',
                'estado_civil': self.procesar_estado_civil(row['estado_civil_id_contacto']),
                'escolaridad': self.procesar_escolaridad(row['id_Escolaridad_contacto']),
                'ocupacion': self.procesar_ocupacion(row['ocupacion_id_contacto'])
            }
        except Exception as e:
            raise ValueError(f"Error procesando datos del encargado: {str(e)}")

    def procesar_datos_matricula(self, row, curso_lectivo, institucion):
        """Procesa los datos de matrícula desde la fila del CSV"""
        try:
            # Obtener nivel y sección de los campos correspondientes
            nivel_str = str(row['Nivel que Matricula']).strip()
            seccion_str = str(row['Sección']).strip()
            
            if pd.isna(nivel_str) or nivel_str == '':
                raise ValueError("Campo 'Nivel que Matricula' es obligatorio para la matrícula")
            
            if pd.isna(seccion_str) or seccion_str == '':
                raise ValueError("Campo 'Sección' es obligatorio para la matrícula")
            
            # Extraer número del nivel (ej: "10 (Decimo)" -> 10)
            nivel_match = re.match(r'(\d+)', nivel_str)
            if not nivel_match:
                raise ValueError(f"Formato inválido de nivel: {nivel_str}. Debe contener un número")
            
            nivel_numero = int(nivel_match.group(1))
            
            # Extraer número de la sección (ej: "10-1" -> 1, "7-5" -> 5)
            seccion_match = re.match(r'\d+-(\d+)', seccion_str)
            if not seccion_match:
                raise ValueError(f"Formato inválido de sección: {seccion_str}. Debe ser como '10-1'")
            
            seccion_numero = int(seccion_match.group(1))
            
            # Obtener nivel, sección y especialidad
            nivel = self.procesar_nivel(nivel_numero)
            if not nivel:
                raise ValueError(f"No se pudo encontrar o crear el nivel {nivel_numero}")
            
            seccion = self.procesar_seccion(seccion_numero, nivel)
            if not seccion:
                raise ValueError(f"No se pudo encontrar o crear la sección {seccion_numero} para el nivel {nivel_numero}")
            
            # La especialidad puede estar vacía para algunos niveles
            especialidad = None
            if not pd.isna(row['Especialidad ']) and str(row['Especialidad ']).strip() != '':
                especialidad = self.procesar_especialidad(row['Especialidad '], curso_lectivo, institucion)
            
            return {
                'nivel': nivel,
                'seccion': seccion,
                'especialidad': especialidad,
                'subgrupo_letra': '',  # No hay letra de subgrupo en este formato
                'curso_lectivo': curso_lectivo,
                'estado': 'activo'
            }
        except Exception as e:
            raise ValueError(f"Error procesando datos de matrícula: {str(e)}")

    def validar_identificacion(self, identificacion):
        """Valida que la identificación no esté vacía"""
        return identificacion and str(identificacion).strip() != ''

    def procesar_fecha(self, fecha_str):
        """Procesa una fecha desde string o pandas datetime"""
        if pd.isna(fecha_str):
            # Si la fecha es nula, retornar la fecha actual
            return timezone.now().date()
        
        if isinstance(fecha_str, str):
            fecha_str = fecha_str.strip()
            if not fecha_str:
                return timezone.now().date()
            
            # Intentar diferentes formatos
            formatos = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']
            for formato in formatos:
                try:
                    return datetime.strptime(fecha_str, formato).date()
                except ValueError:
                    continue
            
            # Si no se puede parsear, retornar fecha actual
            self.stdout.write(
                self.style.WARNING(f"No se pudo parsear la fecha: {fecha_str}. Usando fecha actual.")
            )
            return timezone.now().date()
        
        elif isinstance(fecha_str, pd.Timestamp):
            try:
                return fecha_str.date()
            except:
                return timezone.now().date()
        
        # Para cualquier otro tipo, retornar fecha actual
        return timezone.now().date()

    def procesar_genero(self, genero_id):
        """Procesa el género del estudiante"""
        if pd.isna(genero_id) or genero_id == '':
            # Buscar un género por defecto
            try:
                return Sexo.objects.first()
            except:
                return None
        
        try:
            return Sexo.objects.get(id=genero_id)
        except Sexo.DoesNotExist:
            # Si no existe, crear uno por defecto
            try:
                return Sexo.objects.create(nombre="No especificado")
            except:
                return Sexo.objects.first()

    def procesar_nacionalidad(self, nacionalidad_id):
        """Procesa la nacionalidad del estudiante"""
        if pd.isna(nacionalidad_id) or nacionalidad_id == '':
            # Buscar una nacionalidad por defecto
            try:
                return Nacionalidad.objects.first()
            except:
                return None
        
        try:
            return Nacionalidad.objects.get(id=nacionalidad_id)
        except Nacionalidad.DoesNotExist:
            # Si no existe, crear una por defecto
            try:
                return Nacionalidad.objects.create(nombre="No especificada")
            except:
                return Nacionalidad.objects.first()

    def procesar_tipo_identificacion(self, tipo_identificacion_id):
        """Procesa el tipo de identificación del estudiante"""
        if pd.isna(tipo_identificacion_id) or tipo_identificacion_id == '':
            # Buscar un tipo por defecto
            try:
                return TipoIdentificacion.objects.first()
            except:
                return None
        
        try:
            return TipoIdentificacion.objects.get(id=tipo_identificacion_id)
        except TipoIdentificacion.DoesNotExist:
            # Si no existe, crear uno por defecto
            try:
                return TipoIdentificacion.objects.create(nombre="No especificado")
            except:
                return TipoIdentificacion.objects.first()

    def procesar_parentesco(self, parentesco_id):
        """Procesa el parentesco del estudiante"""
        if pd.isna(parentesco_id) or parentesco_id == '':
            # Buscar un parentesco por defecto
            try:
                return Parentesco.objects.first()
            except:
                return None
        
        try:
            return Parentesco.objects.get(id=parentesco_id)
        except Parentesco.DoesNotExist:
            # Si no existe, crear uno por defecto
            try:
                return Parentesco.objects.create(nombre="No especificado")
            except:
                return Parentesco.objects.first()

    def procesar_nivel(self, nivel_num):
        """Procesa el nivel del estudiante"""
        if pd.isna(nivel_num) or nivel_num == '':
            return None
        
        try:
            nivel_num = int(nivel_num)
            # Buscar nivel por número
            try:
                return Nivel.objects.get(numero=nivel_num)
            except Nivel.DoesNotExist:
                # Si no existe, crear uno por defecto
                try:
                    return Nivel.objects.create(numero=nivel_num, nombre=f"Nivel {nivel_num}")
                except:
                    return Nivel.objects.first()
        except (ValueError, TypeError):
            return Nivel.objects.first()

    def procesar_seccion(self, seccion_num, nivel):
        """Procesa la sección del estudiante"""
        if pd.isna(seccion_num) or seccion_num == '' or not nivel:
            return None
        
        try:
            seccion_num = int(seccion_num)
            # Buscar sección por número y nivel
            try:
                return Seccion.objects.get(numero=seccion_num, nivel=nivel)
            except Seccion.DoesNotExist:
                # Si no existe, crear una por defecto
                try:
                    return Seccion.objects.create(numero=seccion_num, nivel=nivel, nombre=f"Sección {seccion_num}")
                except:
                    return Seccion.objects.first()
        except (ValueError, TypeError):
            return Seccion.objects.first()

    def procesar_especialidad(self, especialidad_str, curso_lectivo, institucion):
        """Procesa la especialidad del estudiante buscando en EspecialidadCursoLectivo"""
        if pd.isna(especialidad_str) or especialidad_str == '':
            return None
        
        especialidad_str = str(especialidad_str).strip()
        if not especialidad_str:
            return None
        
        # Buscar en la tabla EspecialidadCursoLectivo
        try:
            from config_institucional.models import EspecialidadCursoLectivo
            
            especialidad_curso = EspecialidadCursoLectivo.objects.filter(
                especialidad__nombre__icontains=especialidad_str,
                curso_lectivo=curso_lectivo,
                institucion=institucion,
                activa=True
            ).first()
            
            if especialidad_curso:
                return especialidad_curso.especialidad
            else:
                # Si no se encuentra, buscar solo por nombre en Especialidad
                especialidad = Especialidad.objects.filter(nombre__icontains=especialidad_str).first()
                if especialidad:
                    # Crear la relación EspecialidadCursoLectivo si no existe
                    try:
                        EspecialidadCursoLectivo.objects.get_or_create(
                            especialidad=especialidad,
                            curso_lectivo=curso_lectivo,
                            institucion=institucion,
                            defaults={'activa': True}
                        )
                        return especialidad
                    except:
                        return especialidad
                else:
                    # Crear nueva especialidad si no existe
                    try:
                        nueva_especialidad = Especialidad.objects.create(nombre=especialidad_str.upper())
                        EspecialidadCursoLectivo.objects.create(
                            especialidad=nueva_especialidad,
                            curso_lectivo=curso_lectivo,
                            institucion=institucion,
                            defaults={'activa': True}
                        )
                        return nueva_especialidad
                    except:
                        return Especialidad.objects.first()
        except Exception as e:
            # Si hay algún error, usar la primera especialidad disponible
            return Especialidad.objects.first()

    @transaction.atomic
    def crear_estudiante(self, estudiante_data):
        """Crea un nuevo estudiante"""
        try:
            estudiante = Estudiante.objects.create(
                identificacion=estudiante_data['identificacion'],
                nombres=estudiante_data['nombres'],
                primer_apellido=estudiante_data['primer_apellido'],
                segundo_apellido=estudiante_data['segundo_apellido'],
                fecha_nacimiento=estudiante_data['fecha_nacimiento'],
                celular=estudiante_data['celular'],
                sexo=estudiante_data['sexo'],
                nacionalidad=estudiante_data['nacionalidad'],
                tipo_identificacion=estudiante_data['tipo_identificacion'],
                provincia=estudiante_data['provincia'],
                canton=estudiante_data['canton'],
                distrito=estudiante_data['distrito'],
                direccion_exacta=estudiante_data['direccion_exacta'],
                foto=estudiante_data['foto'],
                correo=estudiante_data['correo'],
                adecuacion=estudiante_data['adecuacion'],
                numero_poliza=estudiante_data['numero_poliza'],
                rige_poliza=estudiante_data['rige_poliza'],
                vence_poliza=estudiante_data['vence_poliza'],
                ed_religiosa=estudiante_data['ed_religiosa'],
                presenta_enfermedad=estudiante_data['presenta_enfermedad'],
                detalle_enfermedad=estudiante_data['detalle_enfermedad'],
                medicamentos_consume=estudiante_data['medicamentos_consume'],
                autoriza_derecho_imagen=estudiante_data['autoriza_derecho_imagen'],
                institucion=estudiante_data['institucion']
            )
            
            # Guardar el estudiante en el diccionario para uso posterior
            estudiante_data['estudiante'] = estudiante
            
            self.stdout.write(f"✅ Estudiante creado: {estudiante.nombres} {estudiante.primer_apellido}")
            return estudiante
            
        except Exception as e:
            raise ValueError(f"Error creando estudiante: {str(e)}")

    @transaction.atomic
    def actualizar_estudiante(self, estudiante, estudiante_data):
        """Actualiza un estudiante existente"""
        try:
            estudiante.tipo_estudiante = estudiante_data['tipo_estudiante']
            estudiante.nombres = estudiante_data['nombres']
            estudiante.primer_apellido = estudiante_data['primer_apellido']
            estudiante.segundo_apellido = estudiante_data['segundo_apellido']
            estudiante.fecha_nacimiento = estudiante_data['fecha_nacimiento']
            estudiante.celular = estudiante_data['celular']
            estudiante.sexo = estudiante_data['sexo']
            estudiante.nacionalidad = estudiante_data['nacionalidad']
            estudiante.tipo_identificacion = estudiante_data['tipo_identificacion']
            estudiante.provincia = estudiante_data['provincia']
            estudiante.canton = estudiante_data['canton']
            estudiante.distrito = estudiante_data['distrito']
            estudiante.direccion_exacta = estudiante_data['direccion_exacta']
            estudiante.foto = estudiante_data['foto']
            estudiante.correo = estudiante_data['correo']
            estudiante.adecuacion = estudiante_data['adecuacion']
            estudiante.numero_poliza = estudiante_data['numero_poliza']
            estudiante.rige_poliza = estudiante_data['rige_poliza']
            estudiante.vence_poliza = estudiante_data['vence_poliza']
            estudiante.ed_religiosa = estudiante_data['ed_religiosa']
            estudiante.presenta_enfermedad = estudiante_data['presenta_enfermedad']
            estudiante.detalle_enfermedad = estudiante_data['detalle_enfermedad']
            estudiante.medicamentos_consume = estudiante_data['medicamentos_consume']
            estudiante.autoriza_derecho_imagen = estudiante_data['autoriza_derecho_imagen']
            estudiante.institucion = estudiante_data['institucion']
            estudiante.save()
            
            # Guardar el estudiante en el diccionario para uso posterior
            estudiante_data['estudiante'] = estudiante
            
            self.stdout.write(f"🔄 Estudiante actualizado: {estudiante.nombres} {estudiante.primer_apellido}")
            return estudiante
            
        except Exception as e:
            raise ValueError(f"Error actualizando estudiante: {str(e)}")

    @transaction.atomic
    def procesar_encargado(self, estudiante, encargado_data, row):
        """Procesa y crea/actualiza el encargado del estudiante"""
        try:
            # Crear o actualizar PersonaContacto
            persona_contacto, created = PersonaContacto.objects.get_or_create(
                identificacion=encargado_data['identificacion'],
                defaults={
                    'primer_apellido': encargado_data['apellido1'],
                    'segundo_apellido': encargado_data['apellido2'],
                    'nombres': encargado_data['nombre'],
                    'celular_avisos': encargado_data['celular'],
                    'correo': encargado_data['correo'],
                    'lugar_trabajo': encargado_data['direccion_exacta'],
                    'telefono_trabajo': encargado_data['telefono_casa'],
                    'estado_civil': encargado_data['estado_civil'],
                    'escolaridad': encargado_data['escolaridad'],
                    'ocupacion': encargado_data['ocupacion'],
                    'institucion': estudiante.institucion
                }
            )
            
            if not created:
                # Actualizar campos existentes
                persona_contacto.primer_apellido = encargado_data['apellido1']
                persona_contacto.segundo_apellido = encargado_data['apellido2']
                persona_contacto.nombres = encargado_data['nombre']
                persona_contacto.celular_avisos = encargado_data['celular']
                persona_contacto.correo = encargado_data['correo']
                persona_contacto.lugar_trabajo = encargado_data['direccion_exacta']
                persona_contacto.telefono_trabajo = encargado_data['telefono_casa']
                persona_contacto.estado_civil = encargado_data['estado_civil']
                persona_contacto.escolaridad = encargado_data['escolaridad']
                persona_contacto.ocupacion = encargado_data['ocupacion']
                persona_contacto.save()
            
            # Verificar si ya existe un encargado principal para este estudiante
            encargado_existente = EncargadoEstudiante.objects.filter(
                estudiante=estudiante,
                principal=True
            ).first()
            
            # Crear la relación EncargadoEstudiante
            encargado_estudiante, created = EncargadoEstudiante.objects.get_or_create(
                estudiante=estudiante,
                persona_contacto=persona_contacto,
                defaults={
                    'parentesco': encargado_data['parentesco'],
                    'principal': encargado_existente is None,  # Solo principal si no hay otro
                    'convivencia': str(row.get('Vive con el estudiante_contacto', '')).lower() == 'true' if not pd.isna(row.get('Vive con el estudiante_contacto', '')) else False
                }
            )
            
            if not created:
                # Actualizar parentesco si ya existe
                encargado_estudiante.parentesco = encargado_data['parentesco']
                encargado_estudiante.save()
            
            if created:
                self.stdout.write(f"✅ Encargado creado: {persona_contacto.nombres} {persona_contacto.primer_apellido}")
            else:
                self.stdout.write(f"🔄 Encargado actualizado: {persona_contacto.nombres} {persona_contacto.primer_apellido}")
            
            return encargado_estudiante
            
        except Exception as e:
            raise ValueError(f"Error procesando encargado: {str(e)}")

    @transaction.atomic
    def procesar_matricula(self, estudiante, matricula_data):
        """Procesa y crea/actualiza la matrícula del estudiante"""
        try:
            # Crear o actualizar MatriculaAcademica
            matricula, created = MatriculaAcademica.objects.get_or_create(
                estudiante=estudiante,
                curso_lectivo=matricula_data['curso_lectivo'],
                defaults={
                    'nivel': matricula_data['nivel'],
                    'seccion': matricula_data['seccion'],
                    'especialidad': matricula_data['especialidad'],
                    'estado': matricula_data['estado']
                }
            )
            
            if not created:
                # Actualizar campos existentes
                matricula.nivel = matricula_data['nivel']
                matricula.seccion = matricula_data['seccion']
                matricula.especialidad = matricula_data['especialidad']
                matricula.estado = matricula_data['estado']
                matricula.save()
            
            if created:
                self.stdout.write(f"✅ Matrícula creada para: {estudiante.nombres} {estudiante.primer_apellido}")
            else:
                self.stdout.write(f"🔄 Matrícula actualizada para: {estudiante.nombres} {estudiante.primer_apellido}")
            
            return matricula
            
        except Exception as e:
            raise ValueError(f"Error procesando matrícula: {str(e)}")

    def procesar_estado_civil(self, estado_civil_id):
        """Procesa el estado civil del encargado"""
        if pd.isna(estado_civil_id) or estado_civil_id == '':
            try:
                return EstadoCivil.objects.first()
            except:
                return None
        
        try:
            return EstadoCivil.objects.get(id=estado_civil_id)
        except EstadoCivil.DoesNotExist:
            try:
                return EstadoCivil.objects.first()
            except:
                return None

    def procesar_escolaridad(self, escolaridad_id):
        """Procesa la escolaridad del encargado"""
        if pd.isna(escolaridad_id) or escolaridad_id == '':
            try:
                return Escolaridad.objects.first()
            except:
                return None
        
        try:
            return Escolaridad.objects.get(id=escolaridad_id)
        except Escolaridad.DoesNotExist:
            try:
                return Escolaridad.objects.first()
            except:
                return None

    def procesar_ocupacion(self, ocupacion_id):
        """Procesa la ocupación del encargado"""
        if pd.isna(ocupacion_id) or ocupacion_id == '':
            try:
                return Ocupacion.objects.first()
            except:
                return None
        
        try:
            return Ocupacion.objects.get(id=ocupacion_id)
        except Ocupacion.DoesNotExist:
            try:
                return Ocupacion.objects.first()
            except:
                return None

    def procesar_provincia(self, provincia_id):
        """Procesa la provincia del estudiante"""
        if pd.isna(provincia_id) or provincia_id == '':
            # Buscar una provincia por defecto
            try:
                return Provincia.objects.first()
            except:
                return None
        
        try:
            return Provincia.objects.get(id=provincia_id)
        except Provincia.DoesNotExist:
            # Si no existe, crear una por defecto
            try:
                return Provincia.objects.create(nombre="No especificada")
            except:
                return Provincia.objects.first()

    def procesar_canton(self, canton_id):
        """Procesa el cantón del estudiante"""
        if pd.isna(canton_id) or canton_id == '':
            # Buscar un cantón por defecto
            try:
                return Canton.objects.first()
            except:
                return None
        
        try:
            return Canton.objects.get(id=canton_id)
        except Canton.DoesNotExist:
            # Si no existe, crear uno por defecto
            try:
                return Canton.objects.create(nombre="No especificado")
            except:
                return Canton.objects.first()

    def procesar_distrito(self, distrito_id):
        """Procesa el distrito del estudiante"""
        if pd.isna(distrito_id) or distrito_id == '':
            # Buscar un distrito por defecto
            try:
                return Distrito.objects.first()
            except:
                return None
        
        try:
            return Distrito.objects.get(id=distrito_id)
        except Distrito.DoesNotExist:
            # Si no existe, crear uno por defecto
            try:
                return Distrito.objects.create(nombre="No especificado")
            except:
                return Distrito.objects.first()

    def procesar_adecuacion(self, adecuacion_id):
        """Procesa la adecuación curricular del estudiante"""
        if pd.isna(adecuacion_id) or adecuacion_id == '':
            return None
        
        try:
            return Adecuacion.objects.get(id=adecuacion_id)
        except Adecuacion.DoesNotExist:
            # Si no existe, crear una por defecto
            try:
                return Adecuacion.objects.create(nombre="No especificada")
            except:
                return None

    def mostrar_resultados(self, resultados, dry_run):
        """Muestra el resumen de la importación"""
        if dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 MODO DRY-RUN - No se guardaron datos"))
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("📊 RESUMEN DE LA IMPORTACIÓN")
        self.stdout.write("="*50)
        self.stdout.write(f"✅ Filas válidas: {resultados['validos']}")
        self.stdout.write(f"🆕 Estudiantes creados: {resultados['creados']}")
        self.stdout.write(f"🔄 Estudiantes actualizados: {resultados['actualizados']}")
        self.stdout.write(f"👥 Encargados procesados: {resultados['encargados_creados']}")
        self.stdout.write(f"📚 Matrículas procesadas: {resultados['matriculas_creadas']}")
        self.stdout.write(f"❌ Errores: {resultados['errores']}")
        
        if resultados['errores'] > 0:
            self.stdout.write(self.style.ERROR(f"\n⚠️ Se encontraron {resultados['errores']} errores durante la importación"))
        else:
            self.stdout.write(self.style.SUCCESS("\n🎉 Importación completada exitosamente"))
        
        self.stdout.write("="*50)
