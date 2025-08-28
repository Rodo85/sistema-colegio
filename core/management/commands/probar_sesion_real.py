from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from core.models import Institucion, Miembro

User = get_user_model()

class Command(BaseCommand):
    help = 'Probar la sesión real del usuario y el middleware'

    def handle(self, *args, **options):
        self.stdout.write('🧪 PROBANDO SESIÓN REAL DEL USUARIO')
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
            
            # 3. Verificar sesiones reales
            self.stdout.write('\n📋 VERIFICANDO SESIONES REALES:')
            
            sesiones_usuario = []
            for sesion in Session.objects.all():
                try:
                    data = sesion.get_decoded()
                    user_id = data.get('_auth_user_id')
                    
                    if user_id and str(user_id) == str(user.id):
                        sesiones_usuario.append(sesion)
                        institucion_id = data.get('institucion_id')
                        if institucion_id:
                            self.stdout.write(f'  ✅ Sesión {sesion.session_key}: institución_id = {institucion_id}')
                            try:
                                inst = Institucion.objects.get(pk=institucion_id)
                                self.stdout.write(f'    └─ Institución: {inst.nombre}')
                            except Institucion.DoesNotExist:
                                self.stdout.write(f'    └─ ⚠️  Institución ID {institucion_id} NO EXISTE')
                        else:
                            self.stdout.write(f'  ⚠️  Sesión {sesion.session_key}: sin institución')
                        
                except Exception as e:
                    self.stdout.write(f'  ❌ Error en sesión: {e}')
            
            if not sesiones_usuario:
                self.stdout.write('  📋 Usuario no tiene sesiones activas')
                return
            
            # 4. Simular middleware con sesión real
            self.stdout.write('\n🔧 SIMULANDO MIDDLEWARE CON SESIÓN REAL:')
            
            # Tomar la primera sesión del usuario
            sesion_real = sesiones_usuario[0]
            data_sesion = sesion_real.get_decoded()
            institucion_id_sesion = data_sesion.get('institucion_id')
            
            self.stdout.write(f'  📋 Usando sesión: {sesion_real.session_key}')
            self.stdout.write(f'  📋 Institución en sesión: {institucion_id_sesion}')
            
            if institucion_id_sesion:
                try:
                    inst = Institucion.objects.get(pk=institucion_id_sesion)
                    self.stdout.write(f'  ✅ Institución encontrada: {inst.nombre}')
                    
                    # Verificar que sea la institución correcta del usuario
                    if inst.id == membresias.first().institucion.id:
                        self.stdout.write(f'  ✅ Institución coincide con membresía del usuario')
                    else:
                        self.stdout.write(f'  ⚠️  Institución NO coincide con membresía del usuario')
                        
                except Institucion.DoesNotExist:
                    self.stdout.write(f'  ❌ Institución ID {institucion_id_sesion} NO EXISTE')
            else:
                self.stdout.write(f'  ❌ No hay institución en la sesión')
            
            # 5. Verificar estado del sistema
            self.stdout.write('\n📊 ESTADO DEL SISTEMA:')
            
            # Verificar si el usuario debería tener institución asignada automáticamente
            if membresias.count() == 1:
                inst = membresias.first().institucion
                if inst.activa:
                    self.stdout.write(f'  ✅ Usuario debería tener institución asignada automáticamente')
                    self.stdout.write(f'  ✅ Institución esperada: {inst.nombre} (ID: {inst.id})')
                    
                    if institucion_id_sesion == inst.id:
                        self.stdout.write(f'  ✅ Estado CORRECTO: Usuario tiene institución asignada')
                    else:
                        self.stdout.write(f'  ❌ Estado INCORRECTO: Usuario NO tiene institución asignada')
                        self.stdout.write(f'  🔧 Problema: El middleware no está funcionando correctamente')
                else:
                    self.stdout.write(f'  ⚠️  Institución no está activa: {inst.nombre}')
            elif membresias.count() > 1:
                self.stdout.write(f'  ⚠️  Usuario tiene múltiples instituciones - debe seleccionar')
            else:
                self.stdout.write(f'  ❌ Usuario no tiene membresías')
                
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuario directormaximo@gmail.com no existe')
        except Exception as e:
            self.stdout.write(f'❌ Error durante la prueba: {e}')
            import traceback
            self.stdout.write(traceback.format_exc())







