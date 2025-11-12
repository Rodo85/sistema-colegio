from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from core.middleware import InstitucionMiddleware
from core.models import Institucion, Miembro
from config_institucional.admin import EspecialidadCursoLectivoAdmin
from config_institucional.models import EspecialidadCursoLectivo

User = get_user_model()

class Command(BaseCommand):
    help = 'Probar específicamente el formulario de EspecialidadCursoLectivo'

    def handle(self, *args, **options):
        self.stdout.write('🧪 PROBANDO FORMULARIO DE ESPECIALIDAD CURSO LECTIVO')
        self.stdout.write('=' * 60)
        
        try:
            # 1. Verificar usuario
            user = User.objects.get(email='directormaximo@gmail.com')
            self.stdout.write(f'👤 Usuario: {user.email}')
            self.stdout.write(f'  • ID: {user.id}')
            self.stdout.write(f'  • Es superusuario: {user.is_superuser}')
            
            if user.is_superuser:
                self.stdout.write('✅ Usuario es superusuario - no necesita institución activa')
                return
            
            # 2. Verificar membresías
            membresias = user.membresias.select_related("institucion").all()
            self.stdout.write(f'\n🏢 Membresías: {membresias.count()}')
            
            for m in membresias:
                inst = m.institucion
                self.stdout.write(f'  • {inst.nombre} (ID: {inst.id}) - {m.get_rol_display()}')
                self.stdout.write(f'    Activa: {inst.activa}')
            
            # 3. Simular request completo
            self.stdout.write('\n🔧 Simulando request completo...')
            
            # Crear request
            factory = RequestFactory()
            request = factory.get('/admin/config_institucional/especialidadcursolectivo/add/')
            
            # Aplicar middleware de sesión
            self.stdout.write('  📞 Aplicando SessionMiddleware...')
            session_middleware = SessionMiddleware(lambda req: None)
            session_middleware.process_request(request)
            request.session.save()
            self.stdout.write(f'  ✅ Sesión creada: {request.session.session_key}')
            
            # Aplicar middleware de autenticación
            self.stdout.write('  📞 Aplicando AuthenticationMiddleware...')
            auth_middleware = AuthenticationMiddleware(lambda req: None)
            auth_middleware.process_request(request)
            
            # Simular login exitoso
            request.user = user
            request.session['_auth_user_id'] = str(user.id)
            request.session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
            request.session.save()
            
            self.stdout.write(f'  ✅ Usuario autenticado: {request.user.is_authenticated}')
            self.stdout.write(f'  ✅ User ID en sesión: {request.session.get("_auth_user_id")}')
            
            # 4. Aplicar nuestro middleware
            self.stdout.write('\n🔧 Aplicando InstitucionMiddleware...')
            
            # Crear middleware
            inst_middleware = InstitucionMiddleware(lambda req: None)
            
            # Simular process_request
            self.stdout.write('  📞 Ejecutando process_request...')
            inst_middleware.process_request(request)
            
            # Verificar estado después de process_request
            self.stdout.write(f'  📊 Después de process_request:')
            self.stdout.write(f'    • Institución activa ID: {getattr(request, "institucion_activa_id", None)}')
            self.stdout.write(f'    • Institución en sesión: {request.session.get("institucion_id")}')
            
            # 5. Simular Django Admin
            self.stdout.write('\n🔧 Simulando Django Admin...')
            
            # Crear instancia del admin
            admin_instance = EspecialidadCursoLectivoAdmin(EspecialidadCursoLectivo, None)
            
            # Simular la creación de un formulario
            self.stdout.write('  📞 Creando formulario...')
            
            # Obtener el formulario base
            form_class = admin_instance.get_form(request)
            self.stdout.write(f'  ✅ Clase de formulario: {form_class.__name__}')
            
            # Crear instancia del formulario
            form = form_class()
            self.stdout.write(f'  ✅ Formulario creado: {form}')
            
            # Verificar campos del formulario
            self.stdout.write('\n📊 CAMPOS DEL FORMULARIO:')
            for field_name, field in form.fields.items():
                self.stdout.write(f'  • {field_name}: {type(field).__name__}')
                
                # Si es el campo institución, verificar detalles
                if field_name == 'institucion':
                    self.stdout.write(f'    - Widget: {type(field.widget).__name__}')
                    self.stdout.write(f'    - Queryset: {field.queryset}')
                    self.stdout.write(f'    - Initial: {field.initial}')
                    self.stdout.write(f'    - Required: {field.required}')
                    
                    # Verificar si el campo tiene opciones
                    if hasattr(field, 'choices'):
                        choices = list(field.choices)
                        self.stdout.write(f'    - Choices disponibles: {len(choices)}')
                        for choice in choices[:3]:  # Mostrar solo los primeros 3
                            self.stdout.write(f'      → {choice}')
                        if len(choices) > 3:
                            self.stdout.write(f'      ... y {len(choices) - 3} más')
            
            # 6. Verificar si el campo institución tiene valor inicial
            self.stdout.write('\n🏢 VERIFICACIÓN DEL CAMPO INSTITUCIÓN:')
            if 'institucion' in form.fields:
                field = form.fields['institucion']
                if field.initial:
                    self.stdout.write(f'  ✅ Campo institución tiene valor inicial: {field.initial}')
                    try:
                        inst = Institucion.objects.get(pk=field.initial)
                        self.stdout.write(f'  ✅ Institución inicial: {inst.nombre}')
                    except Institucion.DoesNotExist:
                        self.stdout.write(f'  ❌ Institución inicial no existe en BD')
                else:
                    self.stdout.write(f'  ❌ Campo institución NO tiene valor inicial')
                
                # Verificar queryset
                if field.queryset:
                    self.stdout.write(f'  📋 Queryset del campo: {field.queryset.count()} instituciones')
                    for inst in field.queryset:
                        self.stdout.write(f'    • {inst.nombre} (ID: {inst.id})')
                else:
                    self.stdout.write(f'  ❌ Queryset del campo está vacío')
            else:
                self.stdout.write(f'  ❌ Campo institución no existe en el formulario')
            
            # 7. Simular validación del formulario
            self.stdout.write('\n🔍 SIMULANDO VALIDACIÓN DEL FORMULARIO:')
            
            # Crear datos del formulario
            form_data = {
                'curso_lectivo': '1',  # ID del primer curso lectivo
                'especialidad': '1',   # ID de la primera especialidad
                'activa': True
            }
            
            # Si el campo institución tiene valor inicial, incluirlo
            if 'institucion' in form.fields and form.fields['institucion'].initial:
                form_data['institucion'] = str(form.fields['institucion'].initial)
                self.stdout.write(f'  ✅ Incluyendo institución en datos: {form_data["institucion"]}')
            else:
                self.stdout.write(f'  ❌ No se pudo incluir institución en datos')
            
            # Crear formulario con datos
            form_with_data = form_class(data=form_data)
            self.stdout.write(f'  ✅ Formulario con datos creado')
            
            # Verificar si es válido
            if form_with_data.is_valid():
                self.stdout.write(f'  ✅ Formulario es válido')
                
                # Intentar crear la instancia
                try:
                    instance = form_with_data.save(commit=False)
                    self.stdout.write(f'  ✅ Instancia creada: {instance}')
                    self.stdout.write(f'  ✅ Institución asignada: {instance.institucion_id}')
                    
                    # Verificar que la institución esté asignada
                    if instance.institucion_id:
                        self.stdout.write(f'  ✅ Institución asignada correctamente: {instance.institucion_id}')
                    else:
                        self.stdout.write(f'  ❌ Institución NO asignada')
                        
                except Exception as e:
                    self.stdout.write(f'  ❌ Error al crear instancia: {e}')
            else:
                self.stdout.write(f'  ❌ Formulario NO es válido')
                self.stdout.write(f'  📋 Errores: {form_with_data.errors}')
                
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuario directormaximo@gmail.com no existe')
        except Exception as e:
            self.stdout.write(f'❌ Error durante la prueba: {e}')
            import traceback
            self.stdout.write(traceback.format_exc())
































