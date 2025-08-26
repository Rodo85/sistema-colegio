from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Institucion, Miembro
from django.contrib.sessions.models import Session
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Verificar el estado actual del sistema multi-institucional'

    def handle(self, *args, **options):
        self.stdout.write('🔍 VERIFICACIÓN DEL ESTADO DEL SISTEMA')
        self.stdout.write('=' * 50)
        
        # 1. Verificar instituciones
        self.stdout.write('\n🏢 INSTITUCIONES:')
        instituciones = Institucion.objects.all()
        for inst in instituciones:
            self.stdout.write(f'  • {inst.nombre} (ID: {inst.id})')
            self.stdout.write(f'    - Activa: {inst.activa}')
            self.stdout.write(f'    - Fecha fin: {inst.fecha_fin}')
        
        # 2. Verificar usuarios
        self.stdout.write('\n👥 USUARIOS:')
        usuarios = User.objects.all()
        for user in usuarios:
            self.stdout.write(f'  • {user.email}')
            self.stdout.write(f'    - Superuser: {user.is_superuser}')
            self.stdout.write(f'    - Staff: {user.is_staff}')
            self.stdout.write(f'    - Activo: {user.is_active}')
            
            if not user.is_superuser:
                membresias = user.membresias.all()
                if membresias.exists():
                    for m in membresias:
                        self.stdout.write(f'    - Miembro de: {m.institucion.nombre} ({m.get_rol_display()})')
                else:
                    self.stdout.write(f'    - ⚠️  Sin membresías')
        
        # 3. Verificar sesiones activas
        self.stdout.write('\n📋 SESIONES ACTIVAS:')
        sesiones = Session.objects.filter(expire_date__gt=timezone.now())
        for sesion in sesiones:
            try:
                data = sesion.get_decoded()
                user_id = data.get('_auth_user_id')
                institucion_id = data.get('institucion_id')
                
                if user_id:
                    try:
                        user = User.objects.get(id=user_id)
                        self.stdout.write(f'  • Usuario: {user.email}')
                        if institucion_id:
                            try:
                                inst = Institucion.objects.get(id=institucion_id)
                                self.stdout.write(f'    └─ Institución: {inst.nombre}')
                            except Institucion.DoesNotExist:
                                self.stdout.write(f'    └─ ⚠️  Institución ID {institucion_id} NO EXISTE')
                        else:
                            self.stdout.write(f'    └─ ⚠️  Sin institución seleccionada')
                    except User.DoesNotExist:
                        self.stdout.write(f'  • ⚠️  Usuario ID {user_id} NO EXISTE')
                else:
                    self.stdout.write(f'  • Sesión sin usuario autenticado')
                    
            except Exception as e:
                self.stdout.write(f'  • ⚠️  Error en sesión: {e}')
        
        # 4. Resumen
        self.stdout.write('\n📊 RESUMEN:')
        self.stdout.write(f'  • Total instituciones: {instituciones.count()}')
        self.stdout.write(f'  • Total usuarios: {usuarios.count()}')
        self.stdout.write(f'  • Total sesiones activas: {sesiones.count()}')
        
        # 5. Verificar configuración
        self.stdout.write('\n⚙️  CONFIGURACIÓN:')
        from django.conf import settings
        self.stdout.write(f'  • DEBUG: {settings.DEBUG}')
        self.stdout.write(f'  • MIDDLEWARE: InstitucionMiddleware está en posición {list(settings.MIDDLEWARE).index("core.middleware.InstitucionMiddleware") + 1}')
        
        # Verificar que esté después de AuthenticationMiddleware
        auth_index = list(settings.MIDDLEWARE).index('django.contrib.auth.middleware.AuthenticationMiddleware')
        inst_index = list(settings.MIDDLEWARE).index('core.middleware.InstitucionMiddleware')
        
        if inst_index > auth_index:
            self.stdout.write(f'  ✅ Orden correcto: InstitucionMiddleware después de AuthenticationMiddleware')
        else:
            self.stdout.write(f'  ❌ Orden incorrecto: InstitucionMiddleware debe ir después de AuthenticationMiddleware')

