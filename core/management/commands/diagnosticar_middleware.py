from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Institucion, Miembro
from django.contrib.sessions.models import Session

User = get_user_model()

class Command(BaseCommand):
    help = 'Diagnosticar por qué el middleware no está funcionando'

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
            self.stdout.write(f'  • Es superusuario: {user.is_superuser}')
            
            if user.is_superuser:
                self.stdout.write('✅ Usuario es superusuario - no necesita institución activa')
                return
            
            # Verificar membresías
            if hasattr(user, 'membresias'):
                membresias = user.membresias.select_related('institucion').all()
                self.stdout.write(f'📋 Membresías: {membresias.count()}')
                
                for m in membresias:
                    self.stdout.write(f'  • {m.institucion.nombre} (ID: {m.institucion.id}, Activa: {m.institucion.activa})')
                
                # Filtrar solo las activas
                membresias_activas = [m for m in membresias if m.institucion.activa]
                self.stdout.write(f'✅ Membresías activas: {len(membresias_activas)}')
                
                if len(membresias_activas) == 1:
                    institucion = membresias_activas[0].institucion
                    self.stdout.write(f'\n🎯 Institución única: {institucion.nombre} (ID: {institucion.id})')
                    
                    # Verificar sesiones
                    self.stdout.write('\n🔍 Verificando sesiones...')
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
                    
                    if sesiones_usuario:
                        self.stdout.write(f'\n🔄 Actualizando sesiones con institución {institucion.id}...')
                        sesiones_actualizadas = 0
                        
                        for sesion in sesiones_usuario:
                            try:
                                data = sesion.get_decoded()
                                data['institucion_id'] = institucion.id
                                sesion.session_data = sesion.encode(data)
                                sesion.save()
                                sesiones_actualizadas += 1
                                self.stdout.write(f'  ✅ Sesión {sesion.session_key} actualizada')
                                
                            except Exception as e:
                                self.stdout.write(f'  ❌ Error al actualizar sesión: {e}')
                        
                        if sesiones_actualizadas > 0:
                            self.stdout.write(f'\n✅ ÉXITO:')
                            self.stdout.write(f'  • Sesiones actualizadas: {sesiones_actualizadas}')
                            self.stdout.write(f'  • Institución activa: {institucion.nombre}')
                            self.stdout.write(f'  • request.institucion_activa_id = {institucion.id}')
                            self.stdout.write('\n🔄 AHORA:')
                            self.stdout.write('  1. Recarga la página del admin')
                            self.stdout.write('  2. El botón "Agregar" debería aparecer')
                            self.stdout.write('  3. La institución se asignará automáticamente')
                        else:
                            self.stdout.write('❌ No se pudieron actualizar las sesiones')
                    else:
                        self.stdout.write('ℹ️  No se encontraron sesiones para este usuario')
                        
                elif len(membresias_activas) > 1:
                    self.stdout.write(f'⚠️  Usuario con {len(membresias_activas)} instituciones activas')
                    self.stdout.write('   • Debe seleccionar manualmente su institución')
                    self.stdout.write('   • Ve a /seleccionar-institucion/')
                else:
                    self.stdout.write('❌ Usuario sin membresías activas')
                    
            else:
                self.stdout.write('❌ Usuario sin modelo de membresías')
                
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuario {email} no encontrado')
            return
        
        self.stdout.write('\n✅ Diagnóstico completado')














































