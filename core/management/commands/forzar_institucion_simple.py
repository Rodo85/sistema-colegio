from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Institucion, Miembro
from django.contrib.sessions.models import Session

User = get_user_model()

class Command(BaseCommand):
    help = 'Comando simple para forzar la asignación de institución activa'

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
                self.stdout.write('✅ Usuario es superusuario')
                return
            
            # Verificar membresías
            if hasattr(user, 'membresias'):
                membresias = user.membresias.select_related('institucion').all()
                self.stdout.write(f'📋 Membresías: {membresias.count()}')
                
                # Buscar membresías activas
                membresias_activas = []
                for m in membresias:
                    if m.institucion.activa:
                        membresias_activas.append(m)
                        self.stdout.write(f'  ✅ {m.institucion.nombre} (ID: {m.institucion.id})')
                    else:
                        self.stdout.write(f'  ❌ {m.institucion.nombre} (ID: {m.institucion.id}) - Inactiva')
                
                if not membresias_activas:
                    self.stdout.write('❌ No hay membresías activas')
                    return
                
                if len(membresias_activas) == 1:
                    institucion = membresias_activas[0].institucion
                    self.stdout.write(f'\n🎯 Institución única: {institucion.nombre} (ID: {institucion.id})')
                    
                    # Actualizar sesiones
                    self.stdout.write('\n🔄 Actualizando sesiones...')
                    sesiones_actualizadas = 0
                    
                    for sesion in Session.objects.all():
                        try:
                            data = sesion.get_decoded()
                            user_id = data.get('_auth_user_id')
                            
                            if user_id and str(user_id) == str(user.id):
                                self.stdout.write(f'  📋 Encontrada sesión: {sesion.session_key}')
                                
                                # Actualizar la sesión
                                data['institucion_id'] = institucion.id
                                sesion.session_data = sesion.encode(data)
                                sesion.save()
                                
                                sesiones_actualizadas += 1
                                self.stdout.write(f'  ✅ Sesión actualizada con institución {institucion.id}')
                                
                        except Exception as e:
                            self.stdout.write(f'  ⚠️  Error en sesión: {e}')
                    
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
                    self.stdout.write(f'⚠️  Usuario con {len(membresias_activas)} instituciones activas')
                    self.stdout.write('   • Debe seleccionar manualmente su institución')
                    self.stdout.write('   • Ve a /seleccionar-institucion/')
                    
            else:
                self.stdout.write('❌ Usuario sin modelo de membresías')
                
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuario {email} no encontrado')
            return
        
        self.stdout.write('\n✅ Comando completado')













































