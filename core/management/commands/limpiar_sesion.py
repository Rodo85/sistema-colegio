from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session

User = get_user_model()

class Command(BaseCommand):
    help = 'Limpiar la sesión de un usuario específico'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            type=str,
            required=True,
            help='Email del usuario'
        )

    def handle(self, *args, **options):
        email = options['usuario']
        
        self.stdout.write('🧹 LIMPIANDO SESIÓN DE USUARIO')
        self.stdout.write('=' * 40)
        
        try:
            # 1. Verificar usuario
            user = User.objects.get(email=email)
            self.stdout.write(f'👤 Usuario: {email}')
            self.stdout.write(f'  • ID: {user.id}')
            
            # 2. Buscar sesiones del usuario
            sesiones_usuario = []
            for sesion in Session.objects.all():
                try:
                    data = sesion.get_decoded()
                    user_id = data.get('_auth_user_id')
                    
                    if user_id and str(user_id) == str(user.id):
                        sesiones_usuario.append(sesion)
                        self.stdout.write(f'  📋 Sesión encontrada: {sesion.session_key}')
                        self.stdout.write(f'    • Institución: {data.get("institucion_id", "No asignada")}')
                        
                except Exception as e:
                    self.stdout.write(f'  ⚠️  Error en sesión: {e}')
            
            if not sesiones_usuario:
                self.stdout.write('  📋 Usuario no tiene sesiones activas')
                return
            
            # 3. Limpiar sesiones
            self.stdout.write(f'\n🧹 Limpiando {len(sesiones_usuario)} sesiones...')
            
            for sesion in sesiones_usuario:
                try:
                    # Limpiar institución de la sesión
                    data = sesion.get_decoded()
                    if 'institucion_id' in data:
                        data.pop('institucion_id')
                        sesion.set_expiry(sesion.expire_date)
                        sesion.save()
                        self.stdout.write(f'  ✅ Limpiada institución de sesión: {sesion.session_key}')
                    else:
                        self.stdout.write(f'  ℹ️  Sesión sin institución: {sesion.session_key}')
                        
                except Exception as e:
                    self.stdout.write(f'  ❌ Error limpiando sesión: {e}')
            
            self.stdout.write('\n✅ Sesiones limpiadas correctamente')
            self.stdout.write('  • Ahora puedes hacer login nuevamente para probar la asignación automática')
            
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuario {email} no existe')
        except Exception as e:
            self.stdout.write(f'❌ Error durante la limpieza: {e}')
            import traceback
            self.stdout.write(traceback.format_exc())











