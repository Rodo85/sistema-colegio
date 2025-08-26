from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from core.models import Institucion, Miembro
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)

User = get_user_model()

class Command(BaseCommand):
    help = 'Probar si el signal user_logged_in se ejecuta correctamente'

    def handle(self, *args, **options):
        self.stdout.write('🧪 PROBANDO SIGNAL USER_LOGGED_IN')
        self.stdout.write('=' * 50)
        
        # Variable para capturar el signal
        signal_ejecutado = False
        signal_data = {}
        
        def capturar_signal(sender, user, request, **kwargs):
            nonlocal signal_ejecutado, signal_data
            signal_ejecutado = True
            signal_data = {
                'user': user.email,
                'sender': sender,
                'kwargs': kwargs
            }
            self.stdout.write(f'  📡 Signal capturado para usuario: {user.email}')
        
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
            
            # 3. Simular el signal
            self.stdout.write('\n🔧 Simulando signal user_logged_in...')
            
            # Crear request mock
            class MockRequest:
                def __init__(self):
                    self.session = {}
                
                def get(self, key, default=None):
                    return self.session.get(key, default)
                
                def __setitem__(self, key, value):
                    self.session[key] = value
                
                def save(self):
                    pass
            
            request = MockRequest()
            
            # Disparar el signal manualmente
            user_logged_in.send(sender=User, user=user, request=request)
            
            # 4. Verificar resultado
            self.stdout.write('\n📊 RESULTADO:')
            if signal_ejecutado:
                self.stdout.write('  ✅ Signal se ejecutó correctamente')
                self.stdout.write(f'  📡 Datos del signal: {signal_data}')
            else:
                self.stdout.write('  ❌ Signal no se ejecutó')
            
            # 5. Verificar si se asignó la institución
            self.stdout.write('\n🏢 VERIFICACIÓN DE INSTITUCIÓN:')
            if hasattr(request, 'institucion_activa_id') and request.institucion_activa_id:
                inst = Institucion.objects.get(pk=request.institucion_activa_id)
                self.stdout.write(f'  ✅ Institución asignada: {inst.nombre}')
            else:
                self.stdout.write('  ❌ No se asignó institución')
            
            # Verificar sesión
            institucion_id = request.session.get("institucion_id")
            if institucion_id:
                inst = Institucion.objects.get(pk=institucion_id)
                self.stdout.write(f'  ✅ Institución en sesión: {inst.nombre}')
            else:
                self.stdout.write('  ❌ No hay institución en sesión')
                
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuario directormaximo@gmail.com no existe')
        except Exception as e:
            self.stdout.write(f'❌ Error durante la prueba: {e}')
            import traceback
            self.stdout.write(traceback.format_exc())
