from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Institucion, Miembro
from django.contrib.sessions.models import Session
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Diagnosticar el estado de sesiones y membresías de usuarios'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 DIAGNÓSTICO DE SESIONES Y MEMBRESÍAS'))
        self.stdout.write('=' * 60)
        
        # 1. Verificar instituciones
        self.stdout.write('\n📚 INSTITUCIONES:')
        instituciones = Institucion.objects.all()
        for inst in instituciones:
            self.stdout.write(f'  • {inst.nombre} (ID: {inst.id}, Activa: {inst.activa})')
        
        # 2. Verificar usuarios
        self.stdout.write('\n👥 USUARIOS:')
        usuarios = User.objects.all()
        for user in usuarios:
            self.stdout.write(f'  • {user.email} (Superuser: {user.is_superuser})')
            
            # Verificar membresías
            if hasattr(user, 'membresias'):
                membresias = user.membresias.select_related('institucion').all()
                if membresias.exists():
                    for m in membresias:
                        self.stdout.write(f'    └─ {m.institucion.nombre} (Rol: {m.get_rol_display()})')
                else:
                    self.stdout.write('    └─ Sin membresías')
        
        # 3. Verificar sesiones activas
        self.stdout.write('\n🔐 SESIONES ACTIVAS:')
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
                                self.stdout.write(f'    └─ Institución activa: {inst.nombre} (ID: {inst.id})')
                            except Institucion.DoesNotExist:
                                self.stdout.write(f'    └─ ⚠️  Institución ID {institucion_id} NO EXISTE')
                        else:
                            self.stdout.write('    └─ ⚠️  Sin institución seleccionada')
                    except User.DoesNotExist:
                        self.stdout.write(f'  • ⚠️  Usuario ID {user_id} NO EXISTE')
                else:
                    self.stdout.write('  • Sesión sin usuario autenticado')
                    
            except Exception as e:
                self.stdout.write(f'  • ⚠️  Error al decodificar sesión: {e}')
        
        # 4. Verificar middleware
        self.stdout.write('\n⚙️  ESTADO DEL MIDDLEWARE:')
        self.stdout.write('  • Verificar que InstitucionMiddleware esté en MIDDLEWARE en settings.py')
        self.stdout.write('  • Verificar que la URL /seleccionar-institucion/ esté configurada')
        
        # 5. Recomendaciones
        self.stdout.write('\n💡 RECOMENDACIONES:')
        if not instituciones.exists():
            self.stdout.write('  • ⚠️  No hay instituciones. Crea al menos una institución.')
        else:
            self.stdout.write('  • ✅ Hay instituciones disponibles.')
        
        usuarios_sin_membresias = []
        for user in usuarios:
            if not user.is_superuser and hasattr(user, 'membresias'):
                if not user.membresias.exists():
                    usuarios_sin_membresias.append(user.email)
        
        if usuarios_sin_membresias:
            self.stdout.write(f'  • ⚠️  Usuarios sin membresías: {", ".join(usuarios_sin_membresias)}')
            self.stdout.write('  • 💡 Crea membresías para estos usuarios.')
        else:
            self.stdout.write('  • ✅ Todos los usuarios tienen membresías.')
        
        self.stdout.write('\n🔄 SOLUCIÓN RÁPIDA:')
        self.stdout.write('  1. Cierra sesión en el admin')
        self.stdout.write('  2. Vuelve a iniciar sesión')
        self.stdout.write('  3. Si persiste, ve a /seleccionar-institucion/')
        self.stdout.write('  4. Selecciona tu institución')
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✅ Diagnóstico completado'))




















