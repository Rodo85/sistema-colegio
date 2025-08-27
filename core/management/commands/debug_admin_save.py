from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite
from config_institucional.admin import EspecialidadCursoLectivoAdmin
from config_institucional.models import EspecialidadCursoLectivo
from catalogos.models import CursoLectivo, Especialidad
from core.models import Institucion

User = get_user_model()

class Command(BaseCommand):
    help = 'Debug del admin save_model para EspecialidadCursoLectivo'

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
                    
                    # Simular el admin
                    self.stdout.write('\n🔧 Simulando admin save_model...')
                    
                    # Crear request factory
                    factory = RequestFactory()
                    request = factory.post('/admin/config_institucional/especialidadcursolectivo/add/')
                    request.user = user
                    request.institucion_activa_id = institucion.id
                    request.session = {'institucion_id': institucion.id}
                    
                    # Crear admin instance
                    admin_site = AdminSite()
                    admin_instance = EspecialidadCursoLectivoAdmin(EspecialidadCursoLectivo, admin_site)
                    
                    # Crear objeto de prueba
                    try:
                        curso_lectivo = CursoLectivo.objects.first()
                        especialidad = Especialidad.objects.first()
                        
                        if not curso_lectivo or not especialidad:
                            self.stdout.write('❌ No hay CursoLectivo o Especialidad en la base de datos')
                            return
                        
                        obj = EspecialidadCursoLectivo()
                        obj.curso_lectivo = curso_lectivo
                        obj.especialidad = especialidad
                        obj.activa = True
                        
                        self.stdout.write(f'🔧 Objeto creado:')
                        self.stdout.write(f'  • curso_lectivo: {curso_lectivo.nombre}')
                        self.stdout.write(f'  • especialidad: {especialidad.nombre}')
                        self.stdout.write(f'  • activa: {obj.activa}')
                        
                        # Llamar save_model
                        self.stdout.write('\n🔧 Llamando a save_model...')
                        admin_instance.save_model(request, obj, None, change=False)
                        
                        self.stdout.write(f'\n✅ ÉXITO:')
                        self.stdout.write(f'  • obj.institucion_id = {obj.institucion_id}')
                        self.stdout.write(f'  • obj.institucion = {obj.institucion}')
                        
                    except Exception as e:
                        self.stdout.write(f'\n❌ ERROR en save_model: {e}')
                        import traceback
                        self.stdout.write(f'Traceback: {traceback.format_exc()}')
                        
                elif len(membresias_activas) > 1:
                    self.stdout.write(f'⚠️  Usuario con {len(membresias_activas)} instituciones activas')
                    self.stdout.write('   • Debe seleccionar manualmente su institución')
                else:
                    self.stdout.write('❌ Usuario sin membresías activas')
                    
            else:
                self.stdout.write('❌ Usuario sin modelo de membresías')
                
        except User.DoesNotExist:
            self.stdout.write(f'❌ Usuario {email} no encontrado')
            return
        
        self.stdout.write('\n✅ Debug completado')


















