from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from core.middleware import InstitucionMiddleware
from core.models import Institucion, Miembro

User = get_user_model()

class Command(BaseCommand):
    help = 'Probar el proceso completo de login y asignación de institución'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            type=str,
            required=True,
            help='Email del usuario a probar'
        )
        parser.add_argument(
            '--password',
            type=str,
            required=True,
            help='Contraseña del usuario'
        )

    def handle(self, *args, **options):
        email = options['usuario']
        password = options['password']
        
        self.stdout.write('🧪 PROBANDO PROCESO COMPLETO DE LOGIN')
        self.stdout.write('=' * 50)
        
        try:
            # 1. Verificar que el usuario existe
            user = User.objects.get(email=email)
            self.stdout.write(f'👤 Usuario encontrado: {email}')
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
            
            # 3. Simular el proceso de login completo
            self.stdout.write('\n🔧 Simulando proceso de login...')
            
            # Crear request factory
            factory = RequestFactory()
            request = factory.get('/admin/')
            
            # Aplicar middleware de sesión
            session_middleware = SessionMiddleware(lambda req: None)
            session_middleware.process_request(request)
            request.session.save()
            
            # Aplicar middleware de autenticación
            auth_middleware = AuthenticationMiddleware(lambda req: None)
            auth_middleware.process_request(request)
            
            # Simular login exitoso
            request.user = user
            request.session['_auth_user_id'] = str(user.id)
            request.session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
            request.session.save()
            
            self.stdout.write(f'  ✅ Usuario autenticado en sesión: {request.user.is_authenticated}')
            self.stdout.write(f'  📋 Sesión creada: {request.session.session_key}')
            
            # 4. Aplicar nuestro middleware
            self.stdout.write('\n🔧 Aplicando InstitucionMiddleware...')
            
            # Crear middleware
            inst_middleware = InstitucionMiddleware(lambda req: None)
            
            # Simular __call__
            self.stdout.write('  📞 Ejecutando __call__...')
            inst_middleware.__call__(request)
            
            # Simular process_view
            self.stdout.write('  📞 Ejecutando process_view...')
            inst_middleware.process_view(request, None, [], {})
            
            # 5. Verificar resultado
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

































