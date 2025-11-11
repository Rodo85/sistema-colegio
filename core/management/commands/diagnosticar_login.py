from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Institucion, Miembro
from django.contrib.sessions.models import Session
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = 'Diagnosticar el problema de asignación automática de institución al hacer login'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            type=str,
            required=True,
            help='Email del usuario a diagnosticar'
        )

    def handle(self, *args, **options):
        email = options['usuario']
        
        self.stdout.write('🔍 DIAGNÓSTICO DE LOGIN Y ASIGNACIÓN DE INSTITUCIÓN')
        self.stdout.write('=' * 60)
        
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f'👤 Usuario: {email}')
            self.stdout.write(f'  • ID: {user.id}')
            self.stdout.write(f'  • Es superusuario: {user.is_superuser}')
            self.stdout.write(f'  • Es staff: {user.is_staff}')
            self.stdout.write(f'  • Está activo: {user.is_active}')
            
            if user.is_superuser:
                self.stdout.write('✅ Usuario es superusuario - no necesita institución activa')
                return
            
            # Verificar membresías
            self.stdout.write('\n🏢 MEMBRESÍAS DEL USUARIO:')
            membresias = user.membresias.select_related("institucion").all()
            
            if not membresias.exists():
                self.stdout.write('❌ Usuario NO tiene ninguna membresía')
                return
            
            for i, membresia in enumerate(membresias, 1):
                inst = membresia.institucion
                self.stdout.write(f'  {i}. {inst.nombre} (ID: {inst.id})')
                self.stdout.write(f'     • Rol: {membresia.get_rol_display()}')
                self.stdout.write(f'     • Fecha inicio: {inst.fecha_inicio}')
                self.stdout.write(f'     • Fecha fin: {inst.fecha_fin}')
                self.stdout.write(f'     • Está activa: {inst.activa}')
                self.stdout.write(f'     • Licencia válida: {inst.fecha_fin >= timezone.now().date()}')
            
            # Simular la lógica del middleware
            self.stdout.write('\n🔧 SIMULANDO LÓGICA DEL MIDDLEWARE:')
            
            # 1. Verificar si hay institución en sesión
            self.stdout.write('1️⃣  Verificando sesiones del usuario...')
            sesiones_usuario = []
            
            for sesion in Session.objects.all():
                try:
                    data = sesion.get_decoded()
                    user_id = data.get('_auth_user_id')
                    
                    if user_id and str(user_id) == str(user.id):
                        sesiones_usuario.append(sesion)
                        institucion_id = data.get('institucion_id')
                        if institucion_id:
                            self.stdout.write(f'  📋 Sesión {sesion.session_key}: institución_id = {institucion_id}')
                        else:
                            self.stdout.write(f'  📋 Sesión {sesion.session_key}: sin institución')
                        
                except Exception as e:
                    self.stdout.write(f'  ⚠️  Error en sesión: {e}')
            
            if not sesiones_usuario:
                self.stdout.write('  📋 Usuario no tiene sesiones activas')
            
            # 2. Simular la lógica de asignación automática
            self.stdout.write('\n2️⃣  Simulando asignación automática...')
            
            # Contar membresías válidas
            membresias_validas = [m for m in membresias if m.institucion.activa]
            
            if len(membresias_validas) == 1:
                inst = membresias_validas[0].institucion
                self.stdout.write(f'✅ Usuario tiene EXACTAMENTE 1 institución válida: {inst.nombre}')
                self.stdout.write(f'   → Debería asignarse automáticamente')
                self.stdout.write(f'   → institución_id = {inst.id}')
            elif len(membresias_validas) > 1:
                self.stdout.write(f'⚠️  Usuario tiene {len(membresias_validas)} instituciones válidas')
                self.stdout.write(f'   → Debería ir a pantalla de selección')
            else:
                self.stdout.write(f'❌ Usuario NO tiene instituciones válidas')
                self.stdout.write(f'   → Todas las licencias han expirado')
            
            # 3. Verificar si hay algún problema con el modelo
            self.stdout.write('\n3️⃣  Verificando integridad del modelo...')
            
            for membresia in membresias:
                try:
                    # Verificar que la relación funciona
                    inst = membresia.institucion
                    self.stdout.write(f'  ✅ Relación {membresia.usuario.email} → {inst.nombre} OK')
                except Exception as e:
                    self.stdout.write(f'  ❌ Error en relación: {e}')
            
            # 4. Recomendaciones
            self.stdout.write('\n💡 RECOMENDACIONES:')
            
            if len(membresias_validas) == 1:
                self.stdout.write('  • El usuario debería tener institución asignada automáticamente')
                self.stdout.write('  • Verificar que el middleware se ejecute después del login')
                self.stdout.write('  • Verificar que la sesión se guarde correctamente')
            elif len(membresias_validas) > 1:
                self.stdout.write('  • El usuario debe seleccionar institución manualmente')
                self.stdout.write('  • Verificar que la vista de selección funcione')
            else:
                self.stdout.write('  • Usuario no tiene instituciones válidas')
                self.stdout.write('  • Contactar al administrador para renovar licencias')
                
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuario {email} no existe')
        except Exception as e:
            self.stdout.write(f'❌ Error durante el diagnóstico: {e}')






























