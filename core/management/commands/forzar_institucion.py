from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Institucion, Miembro
from django.contrib.sessions.models import Session

User = get_user_model()

class Command(BaseCommand):
    help = 'Forzar la asignación de institución activa a un usuario'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            type=str,
            required=True,
            help='Email del usuario'
        )
        parser.add_argument(
            '--institucion',
            type=int,
            help='ID de la institución (opcional, si no se especifica se usa la primera disponible)'
        )

    def handle(self, *args, **options):
        email = options['usuario']
        institucion_id = options.get('institucion')
        
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f'🔍 Usuario encontrado: {email}')
            
            # Verificar membresías
            if hasattr(user, 'membresias'):
                membresias = user.membresias.select_related('institucion').all()
                # Filtrar por institución activa después de obtener los datos
                membresias_activas = [m for m in membresias if m.institucion.activa]
                
                if not membresias_activas:
                    self.stdout.write(self.style.ERROR('❌ El usuario no tiene membresías activas'))
                    return
                
                self.stdout.write(f'📋 Membresías activas encontradas: {len(membresias_activas)}')
                for m in membresias_activas:
                    self.stdout.write(f'  • {m.institucion.nombre} (ID: {m.institucion.id})')
                
                # Seleccionar institución
                if institucion_id:
                    try:
                        institucion = Institucion.objects.get(id=institucion_id, activa=True)
                        if not any(m.institucion.id == institucion.id for m in membresias_activas):
                            self.stdout.write(self.style.ERROR(f'❌ El usuario no tiene membresía en la institución {institucion.nombre}'))
                            return
                    except Institucion.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'❌ Institución ID {institucion_id} no encontrada o no activa'))
                        return
                else:
                    # Usar la primera membresía disponible
                    institucion = membresias_activas[0].institucion
                
                self.stdout.write(f'🎯 Institución seleccionada: {institucion.nombre} (ID: {institucion.id})')
                
                # Buscar y actualizar sesiones del usuario
                sesiones_actualizadas = 0
                for sesion in Session.objects.all():
                    try:
                        data = sesion.get_decoded()
                        user_id = data.get('_auth_user_id')
                        if user_id and str(user_id) == str(user.id):
                            # Actualizar la sesión
                            data['institucion_id'] = institucion.id
                            sesion.session_data = sesion.encode(data)
                            sesion.save()
                            sesiones_actualizadas += 1
                            self.stdout.write(f'  ✅ Sesión actualizada: {sesion.session_key}')
                    except Exception as e:
                        self.stdout.write(f'  ⚠️  Error al actualizar sesión {sesion.session_key}: {e}')
                
                if sesiones_actualizadas > 0:
                    self.stdout.write(f'\n✅ Se actualizaron {sesiones_actualizadas} sesiones')
                    self.stdout.write(f'✅ Institución activa establecida: {institucion.nombre}')
                    self.stdout.write('\n🔄 PRÓXIMOS PASOS:')
                    self.stdout.write('  1. Recarga la página del admin')
                    self.stdout.write('  2. El botón "Agregar" debería aparecer ahora')
                    self.stdout.write('  3. La institución se asignará automáticamente al crear registros')
                else:
                    self.stdout.write(self.style.WARNING('⚠️  No se encontraron sesiones activas para actualizar'))
                    self.stdout.write('💡 El usuario debe cerrar sesión y volver a iniciar sesión')
                
            else:
                self.stdout.write(self.style.ERROR('❌ El usuario no tiene el modelo de membresías'))
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Usuario {email} no encontrado'))
            return
        
        self.stdout.write('\n✅ Comando completado')
