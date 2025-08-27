from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session

User = get_user_model()

class Command(BaseCommand):
    help = 'Limpiar sesiones del usuario y forzar reautenticación'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            type=str,
            required=True,
            help='Email del usuario'
        )

    def handle(self, *args, **options):
        email = options['usuario']
        
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f'🔍 Usuario: {email}')
            
            if user.is_superuser:
                self.stdout.write('✅ Usuario es superusuario - no necesita limpieza')
                return
            
            # Buscar y eliminar todas las sesiones del usuario
            self.stdout.write('\n🗑️  Buscando sesiones del usuario...')
            sesiones_eliminadas = 0
            
            for sesion in Session.objects.all():
                try:
                    data = sesion.get_decoded()
                    user_id = data.get('_auth_user_id')
                    
                    if user_id and str(user_id) == str(user.id):
                        self.stdout.write(f'  📋 Encontrada sesión: {sesion.session_key}')
                        sesion.delete()
                        sesiones_eliminadas += 1
                        self.stdout.write(f'  ✅ Sesión eliminada')
                        
                except Exception as e:
                    self.stdout.write(f'  ⚠️  Error al procesar sesión: {e}')
            
            if sesiones_eliminadas > 0:
                self.stdout.write(f'\n✅ ÉXITO:')
                self.stdout.write(f'  • Sesiones eliminadas: {sesiones_eliminadas}')
                self.stdout.write(f'  • Usuario: {email}')
                self.stdout.write('\n🔄 PRÓXIMOS PASOS:')
                self.stdout.write('  1. Cierra sesión en el admin (si estás logueado)')
                self.stdout.write('  2. Vuelve a iniciar sesión con tu usuario')
                self.stdout.write('  3. El middleware detectará automáticamente tu institución')
                self.stdout.write('  4. El botón "Agregar" debería aparecer')
                self.stdout.write('  5. La institución se asignará automáticamente')
            else:
                self.stdout.write('ℹ️  No se encontraron sesiones para eliminar')
                self.stdout.write('💡 El usuario debe cerrar sesión y volver a iniciar sesión')
                
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuario {email} no encontrado')
            return
        
        self.stdout.write('\n✅ Comando completado')


















