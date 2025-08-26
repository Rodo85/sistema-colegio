from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from core.middleware import InstitucionMiddleware
from core.models import Institucion, Miembro
import logging

# Configurar logging para ver los mensajes del middleware
logging.basicConfig(level=logging.DEBUG)

User = get_user_model()

class Command(BaseCommand):
    help = 'Simular el login real y verificar que el middleware funcione'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            type=str,
            required=True,
            help='Email del usuario a probar'
        )

    def handle(self, *args, **options):
        email = options['usuario']
        
        self.stdout.write('🧪 SIMULANDO LOGIN REAL')
        self.stdout.write('=' * 40)
        
        try:
            # 1. Verificar usuario
            user = User.objects.get(email=email)
            self.stdout.write(f'👤 Usuario: {email}')
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
            request = factory.get('/admin/')
            
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
            
            # Simular __call__ (se ejecuta en process_request)
            self.stdout.write('  📞 Ejecutando __call__ (process_request)...')
            inst_middleware.__call__(request)
            
            # Verificar estado después de __call__
            self.stdout.write(f'  📊 Después de __call__:')
            self.stdout.write(f'    • Institución activa ID: {getattr(request, "institucion_activa_id", None)}')
            self.stdout.write(f'    • Institución en sesión: {request.session.get("institucion_id")}')
            
            # Simular process_view
            self.stdout.write('  📞 Ejecutando process_view...')
            inst_middleware.process_view(request, None, [], {})
            
            # Verificar estado después de process_view
            self.stdout.write(f'  📊 Después de process_view:')
            self.stdout.write(f'    • Institución activa ID: {getattr(request, "institucion_activa_id", None)}')
            self.stdout.write(f'    • Institución en sesión: {request.session.get("institucion_id")}')
            
            # Simular process_response
            self.stdout.write('  📞 Ejecutando process_response...')
            from django.http import HttpResponse
            response = HttpResponse("Test")
            response = inst_middleware.process_response(request, response)
            
            # Verificar estado después de process_response
            self.stdout.write(f'  📊 Después de process_response:')
            self.stdout.write(f'    • Institución activa ID: {getattr(request, "institucion_activa_id", None)}')
            self.stdout.write(f'    • Institución en sesión: {request.session.get("institucion_id")}')
            
            # 5. Resultado final
            self.stdout.write('\n📊 RESULTADO FINAL:')
            self.stdout.write(f'  • Institución activa ID: {getattr(request, "institucion_activa_id", None)}')
            self.stdout.write(f'  • Institución en sesión: {request.session.get("institucion_id")}')
            
            if hasattr(request, 'institucion_activa_id') and request.institucion_activa_id:
                inst = Institucion.objects.get(pk=request.institucion_activa_id)
                self.stdout.write(f'  ✅ Institución asignada correctamente: {inst.nombre}')
            else:
                self.stdout.write('  ❌ No se pudo asignar institución automáticamente')
                
                # Verificar por qué no funcionó
                if membresias.count() == 1:
                    inst = membresias.first().institucion
                    if inst.activa:
                        self.stdout.write('  🔍 Usuario debería tener institución asignada automáticamente')
                        self.stdout.write('  🔍 Verificar logs del middleware')
                    else:
                        self.stdout.write('  🔍 Institución no está activa')
                elif membresias.count() > 1:
                    self.stdout.write('  🔍 Usuario tiene múltiples instituciones - debe seleccionar')
                else:
                    self.stdout.write('  🔍 Usuario no tiene membresías')
                    
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuario {email} no existe')
        except Exception as e:
            self.stdout.write(f'❌ Error durante la prueba: {e}')
            import traceback
            self.stdout.write(traceback.format_exc())

