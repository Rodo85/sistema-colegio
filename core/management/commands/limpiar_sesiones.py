from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from core.models import Institucion, Miembro

User = get_user_model()

class Command(BaseCommand):
    help = 'Limpiar sesiones y forzar reconfiguración de instituciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            type=str,
            help='Email del usuario específico a limpiar'
        )
        parser.add_argument(
            '--todos',
            action='store_true',
            help='Limpiar todas las sesiones'
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Forzar limpieza incluso si hay sesiones activas'
        )

    def handle(self, *args, **options):
        if options['todos']:
            self.stdout.write('🗑️  LIMPIANDO TODAS LAS SESIONES...')
            count = Session.objects.count()
            Session.objects.all().delete()
            self.stdout.write(f'✅ Se eliminaron {count} sesiones')
            
        elif options['usuario']:
            email = options['usuario']
            try:
                user = User.objects.get(email=email)
                self.stdout.write(f'🔍 Buscando sesiones para usuario: {email}')
                
                # Buscar sesiones que contengan este usuario
                sesiones_usuario = []
                for sesion in Session.objects.all():
                    try:
                        data = sesion.get_decoded()
                        user_id = data.get('_auth_user_id')
                        if user_id and str(user_id) == str(user.id):
                            sesiones_usuario.append(sesion)
                    except:
                        continue
                
                if sesiones_usuario:
                    self.stdout.write(f'📋 Encontradas {len(sesiones_usuario)} sesiones para {email}')
                    for sesion in sesiones_usuario:
                        sesion.delete()
                        self.stdout.write(f'  ✅ Sesión eliminada: {sesion.session_key}')
                else:
                    self.stdout.write(f'ℹ️  No se encontraron sesiones para {email}')
                    
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Usuario {email} no encontrado'))
                return
        else:
            self.stdout.write(self.style.WARNING('⚠️  Debes especificar --usuario EMAIL o --todos'))
            self.stdout.write('Ejemplos:')
            self.stdout.write('  python manage.py limpiar_sesiones --usuario directormaximo@gmail.com')
            self.stdout.write('  python manage.py limpiar_sesiones --todos')
            return
        
        # Mostrar estado actual
        self.stdout.write('\n📊 ESTADO ACTUAL:')
        self.stdout.write(f'  • Sesiones activas: {Session.objects.count()}')
        
        # Mostrar usuarios con membresías
        self.stdout.write('\n👥 USUARIOS CON MEMBRESÍAS:')
        usuarios_con_membresias = User.objects.filter(membresias__isnull=False).distinct()
        for user in usuarios_con_membresias:
            membresias = user.membresias.select_related('institucion').all()
            self.stdout.write(f'  • {user.email}:')
            for m in membresias:
                self.stdout.write(f'    └─ {m.institucion.nombre} (ID: {m.institucion.id})')
        
        self.stdout.write('\n🔄 PRÓXIMOS PASOS:')
        self.stdout.write('  1. Cierra sesión en el admin')
        self.stdout.write('  2. Vuelve a iniciar sesión')
        self.stdout.write('  3. El middleware detectará automáticamente tu institución')
        self.stdout.write('  4. Si persiste, ve a /seleccionar-institucion/')
        
        self.stdout.write('\n✅ Comando completado')










































