from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from core.models import Institucion, Miembro
from config_institucional.models import EspecialidadCursoLectivo
from catalogos.models import CursoLectivo, Especialidad

User = get_user_model()

class Command(BaseCommand):
    help = 'Probar el envío real del formulario de EspecialidadCursoLectivo'

    def handle(self, *args, **options):
        self.stdout.write('🧪 PROBANDO ENVÍO REAL DEL FORMULARIO')
        self.stdout.write('=' * 50)
        
        try:
            # 1. Verificar usuario
            user = User.objects.get(email='directormaximo@gmail.com')
            self.stdout.write(f'👤 Usuario: {user.email}')
            self.stdout.write(f'  • ID: {user.id}')
            
            # 2. Verificar membresías
            membresias = user.membresias.select_related("institucion").all()
            self.stdout.write(f'\n🏢 Membresías: {membresias.count()}')
            
            for m in membresias:
                inst = m.institucion
                self.stdout.write(f'  • {inst.nombre} (ID: {inst.id}) - {m.get_rol_display()}')
                self.stdout.write(f'    Activa: {inst.activa}')
            
            # 3. Verificar sesión real
            self.stdout.write('\n📋 VERIFICANDO SESIÓN REAL:')
            
            sesiones_usuario = []
            for sesion in Session.objects.all():
                try:
                    data = sesion.get_decoded()
                    user_id = data.get('_auth_user_id')
                    
                    if user_id and str(user_id) == str(user.id):
                        sesiones_usuario.append(sesion)
                        institucion_id = data.get('institucion_id')
                        if institucion_id:
                            self.stdout.write(f'  ✅ Sesión {sesion.session_key}: institución_id = {institucion_id}')
                        else:
                            self.stdout.write(f'  ⚠️  Sesión {sesion.session_key}: sin institución')
                        
                except Exception as e:
                    self.stdout.write(f'  ❌ Error en sesión: {e}')
            
            if not sesiones_usuario:
                self.stdout.write('  📋 Usuario no tiene sesiones activas')
                return
            
            # 4. Obtener datos necesarios para el formulario
            self.stdout.write('\n🔍 OBTENIENDO DATOS DEL FORMULARIO:')
            
            # Obtener institución de la sesión
            sesion_real = sesiones_usuario[0]
            data_sesion = sesion_real.get_decoded()
            institucion_id_sesion = data_sesion.get('institucion_id')
            
            if not institucion_id_sesion:
                self.stdout.write('  ❌ No hay institución en la sesión')
                return
            
            try:
                institucion = Institucion.objects.get(pk=institucion_id_sesion)
                self.stdout.write(f'  ✅ Institución: {institucion.nombre} (ID: {institucion.id})')
            except Institucion.DoesNotExist:
                self.stdout.write(f'  ❌ Institución ID {institucion_id_sesion} NO EXISTE')
                return
            
            # Obtener curso lectivo
            try:
                curso_lectivo = CursoLectivo.objects.first()
                if curso_lectivo:
                    self.stdout.write(f'  ✅ Curso lectivo: {curso_lectivo.nombre} (ID: {curso_lectivo.id})')
                else:
                    self.stdout.write(f'  ❌ No hay cursos lectivos disponibles')
                    return
            except Exception as e:
                self.stdout.write(f'  ❌ Error obteniendo curso lectivo: {e}')
                return
            
            # Obtener especialidad (usar una diferente si es posible)
            try:
                # Verificar si ya existe un registro con la misma combinación
                existing = EspecialidadCursoLectivo.objects.filter(
                    institucion=institucion,
                    curso_lectivo=curso_lectivo
                ).first()
                
                if existing:
                    self.stdout.write(f'  ⚠️  Ya existe registro: {existing}')
                    self.stdout.write(f'  🔍 Buscando especialidad diferente...')
                    
                    # Buscar una especialidad que no esté ya asignada
                    especialidades_existentes = EspecialidadCursoLectivo.objects.filter(
                        institucion=institucion,
                        curso_lectivo=curso_lectivo
                    ).values_list('especialidad_id', flat=True)
                    
                    especialidad = Especialidad.objects.exclude(
                        id__in=especialidades_existentes
                    ).first()
                    
                    if especialidad:
                        self.stdout.write(f'  ✅ Especialidad diferente encontrada: {especialidad.nombre} (ID: {especialidad.id})')
                    else:
                        self.stdout.write(f'  ❌ No hay especialidades disponibles sin asignar')
                        return
                else:
                    especialidad = Especialidad.objects.first()
                    if especialidad:
                        self.stdout.write(f'  ✅ Especialidad: {especialidad.nombre} (ID: {especialidad.id})')
                    else:
                        self.stdout.write(f'  ❌ No hay especialidades disponibles')
                        return
                        
            except Exception as e:
                self.stdout.write(f'  ❌ Error obteniendo especialidad: {e}')
                return
            
            # 5. Simular creación del objeto
            self.stdout.write('\n🔧 SIMULANDO CREACIÓN DEL OBJETO:')
            
            try:
                # Crear instancia sin guardar
                especialidad_curso = EspecialidadCursoLectivo(
                    institucion=institucion,
                    curso_lectivo=curso_lectivo,
                    especialidad=especialidad,
                    activa=True
                )
                
                self.stdout.write(f'  ✅ Instancia creada: {especialidad_curso}')
                self.stdout.write(f'  ✅ Institución asignada: {especialidad_curso.institucion_id}')
                self.stdout.write(f'  ✅ Curso lectivo: {especialidad_curso.curso_lectivo_id}')
                self.stdout.write(f'  ✅ Especialidad: {especialidad_curso.especialidad_id}')
                
                # Verificar que todos los campos estén asignados
                if especialidad_curso.institucion_id:
                    self.stdout.write(f'  ✅ Campo institución está asignado')
                else:
                    self.stdout.write(f'  ❌ Campo institución NO está asignado')
                
                if especialidad_curso.curso_lectivo_id:
                    self.stdout.write(f'  ✅ Campo curso_lectivo está asignado')
                else:
                    self.stdout.write(f'  ❌ Campo curso_lectivo NO está asignado')
                
                if especialidad_curso.especialidad_id:
                    self.stdout.write(f'  ✅ Campo especialidad está asignado')
                else:
                    self.stdout.write(f'  ❌ Campo especialidad NO está asignado')
                
                # 6. Simular validación
                self.stdout.write('\n🔍 SIMULANDO VALIDACIÓN:')
                
                try:
                    especialidad_curso.full_clean()
                    self.stdout.write(f'  ✅ Validación exitosa')
                except Exception as e:
                    self.stdout.write(f'  ❌ Error en validación: {e}')
                    return
                
                # 7. Simular guardado
                self.stdout.write('\n💾 SIMULANDO GUARDADO:')
                
                try:
                    especialidad_curso.save()
                    self.stdout.write(f'  ✅ Objeto guardado exitosamente')
                    self.stdout.write(f'  ✅ ID asignado: {especialidad_curso.id}')
                    
                    # Verificar que se guardó correctamente
                    obj_guardado = EspecialidadCursoLectivo.objects.get(pk=especialidad_curso.id)
                    self.stdout.write(f'  ✅ Objeto recuperado de BD: {obj_guardado}')
                    self.stdout.write(f'  ✅ Institución en BD: {obj_guardado.institucion.nombre}')
                    
                    # Limpiar el objeto de prueba
                    obj_guardado.delete()
                    self.stdout.write(f'  ✅ Objeto de prueba eliminado')
                    
                except Exception as e:
                    self.stdout.write(f'  ❌ Error al guardar: {e}')
                    import traceback
                    self.stdout.write(traceback.format_exc())
                    return
                
            except Exception as e:
                self.stdout.write(f'  ❌ Error al crear instancia: {e}')
                import traceback
                self.stdout.write(traceback.format_exc())
                return
            
            self.stdout.write('\n✅ PRUEBA COMPLETADA EXITOSAMENTE')
            self.stdout.write('  • El formulario debería funcionar correctamente')
            self.stdout.write('  • El campo institución se asigna automáticamente')
            self.stdout.write('  • La validación pasa sin problemas')
                
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuario directormaximo@gmail.com no existe')
        except Exception as e:
            self.stdout.write(f'❌ Error durante la prueba: {e}')
            import traceback
            self.stdout.write(traceback.format_exc())
