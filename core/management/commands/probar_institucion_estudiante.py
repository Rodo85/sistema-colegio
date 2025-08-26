from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Institucion
from matricula.models import Estudiante
from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite

User = get_user_model()

class Command(BaseCommand):
    help = 'Prueba la asignación automática de institución en el admin de estudiantes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            type=str,
            help='Email del usuario a probar'
        )
        parser.add_argument(
            '--institucion',
            type=str,
            help='ID o nombre de la institución'
        )

    def handle(self, *args, **options):
        usuario_email = options['usuario']
        institucion_id = options['institucion']

        if not usuario_email:
            self.stdout.write(
                self.style.ERROR('Debe especificar un usuario con --usuario')
            )
            return

        try:
            usuario = User.objects.get(email=usuario_email)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Usuario {usuario_email} no encontrado')
            )
            return

        # Obtener institución
        if institucion_id:
            try:
                if institucion_id.isdigit():
                    institucion = Institucion.objects.get(id=institucion_id)
                else:
                    institucion = Institucion.objects.get(nombre__icontains=institucion_id)
            except Institucion.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Institución {institucion_id} no encontrada')
                )
                return
        else:
            # Usar la primera institución disponible
            institucion = Institucion.objects.first()
            if not institucion:
                self.stdout.write(
                    self.style.ERROR('No hay instituciones disponibles')
                )
                return

        self.stdout.write(f'Probando con usuario: {usuario.email}')
        self.stdout.write(f'Institución: {institucion.nombre}')

        # Simular request
        factory = RequestFactory()
        request = factory.get('/admin/matricula/estudiante/add/')
        request.user = usuario
        request.institucion_activa_id = institucion.id

        # Simular admin
        from matricula.admin import EstudianteAdmin
        admin_site = AdminSite()
        admin = EstudianteAdmin(Estudiante, admin_site)

        try:
            # Probar get_form
            form = admin.get_form(request)()
            self.stdout.write(
                self.style.SUCCESS('✓ Formulario creado correctamente')
            )

            # Verificar si el campo institución está presente
            if 'institucion' in form.fields:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Campo institución presente en formulario')
                )
                # Verificar valor inicial
                initial_value = form.fields['institucion'].initial
                if initial_value:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Valor inicial: {initial_value}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('⚠ Campo institución sin valor inicial')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠ Campo institución no presente en formulario')
                )

            # Probar get_fieldsets
            fieldsets = admin.get_fieldsets(request)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Fieldsets creados: {len(fieldsets)}')
            )

            # Mostrar campos disponibles
            campos_disponibles = []
            for name, fieldset in fieldsets:
                campos_disponibles.extend(fieldset['fields'])
            
            self.stdout.write(f'Campos disponibles: {campos_disponibles}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error: {str(e)}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())

        self.stdout.write('\n' + '='*50)
        self.stdout.write('RESUMEN DE LA PRUEBA:')
        self.stdout.write(f'• Usuario: {usuario.email}')
        self.stdout.write(f'• Institución: {institucion.nombre}')
        self.stdout.write(f'• Es superusuario: {usuario.is_superuser}')
        self.stdout.write(f'• Institución activa en request: {getattr(request, "institucion_activa_id", None)}')
