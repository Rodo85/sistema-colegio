from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from core.middleware import InstitucionMiddleware
from core.models import Institucion, Miembro
from matricula.admin import PersonaContactoAdmin
from matricula.models import PersonaContacto

User = get_user_model()

class Command(BaseCommand):
    help = 'Probar cómo Django Admin renderiza un formulario para verificar el campo institución'

    def handle(self, *args, **options):
        self.stdout.write('🧪 PROBANDO FORMULARIO DE DJANGO ADMIN')
        self.stdout.write('=' * 50)
        
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
            request = factory.get('/admin/matricula/personacontacto/add/')
            
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
            admin_instance = PersonaContactoAdmin(PersonaContacto, None)
            
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
                
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuario directormaximo@gmail.com no existe')
        except Exception as e:
            self.stdout.write(f'❌ Error durante la prueba: {e}')
            import traceback
            self.stdout.write(traceback.format_exc())








