from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Institucion
from matricula.models import Estudiante
from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite
from django import forms

User = get_user_model()

class Command(BaseCommand):
    help = 'Debug del formulario de estudiante para ver problemas con la institución'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            type=str,
            help='Email del usuario a probar'
        )

    def handle(self, *args, **options):
        usuario_email = options['usuario']

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

        # Obtener institución del usuario
        try:
            membresia = usuario.membresias.first()
            if not membresia:
                self.stdout.write(
                    self.style.ERROR('Usuario no tiene membresías')
                )
                return
            institucion = membresia.institucion
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error obteniendo institución: {e}')
            )
            return

        self.stdout.write(f'Probando con usuario: {usuario.email}')
        self.stdout.write(f'Institución: {institucion.nombre} (ID: {institucion.id})')
        self.stdout.write(f'Es superusuario: {usuario.is_superuser}')

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
            form_class = admin.get_form(request)
            self.stdout.write(
                self.style.SUCCESS('✓ Clase de formulario obtenida')
            )
            
            # Crear instancia del formulario
            form = form_class()
            self.stdout.write(
                self.style.SUCCESS('✓ Instancia de formulario creada')
            )

            # Verificar campos del formulario
            self.stdout.write('\n' + '='*50)
            self.stdout.write('CAMPOS DEL FORMULARIO:')
            
            for field_name, field in form.fields.items():
                self.stdout.write(f'\nCampo: {field_name}')
                self.stdout.write(f'  - Tipo: {type(field).__name__}')
                self.stdout.write(f'  - Requerido: {field.required}')
                self.stdout.write(f'  - Inicial: {field.initial}')
                self.stdout.write(f'  - Widget: {type(field.widget).__name__}')
                
                if field_name == 'institucion':
                    self.stdout.write(f'  - Queryset: {field.queryset.count()} opciones')
                    if field.queryset.exists():
                        self.stdout.write(f'  - Primera opción: {field.queryset.first()}')

            # Verificar si el campo institución está presente
            if 'institucion' in form.fields:
                self.stdout.write(
                    self.style.SUCCESS('\n✓ Campo institución presente en formulario')
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
                
                # Verificar si el campo está deshabilitado
                if hasattr(form.fields['institucion'], 'disabled'):
                    self.stdout.write(f'  - Deshabilitado: {form.fields["institucion"].disabled}')
                
            else:
                self.stdout.write(
                    self.style.WARNING('\n⚠ Campo institución NO presente en formulario')
                )

            # Probar get_fieldsets
            fieldsets = admin.get_fieldsets(request)
            self.stdout.write(f'\n✓ Fieldsets creados: {len(fieldsets)}')
            
            # Mostrar campos disponibles en fieldsets
            campos_disponibles = []
            for name, fieldset in fieldsets:
                campos_disponibles.extend(fieldset['fields'])
            
            self.stdout.write(f'Campos en fieldsets: {campos_disponibles}')

            # Verificar si 'institucion' está en los fieldsets
            if 'institucion' in campos_disponibles:
                self.stdout.write(
                    self.style.SUCCESS('✓ Campo institución incluido en fieldsets')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠ Campo institución NO incluido en fieldsets')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Error: {str(e)}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())

        self.stdout.write('\n' + '='*50)
        self.stdout.write('RESUMEN DE LA PRUEBA:')
        self.stdout.write(f'• Usuario: {usuario.email}')
        self.stdout.write(f'• Institución: {institucion.nombre} (ID: {institucion.id})')
        self.stdout.write(f'• Es superusuario: {usuario.is_superuser}')
        self.stdout.write(f'• Institución activa en request: {getattr(request, "institucion_activa_id", None)}')
        
        # Verificar si hay diferencias
        if getattr(request, 'institucion_activa_id', None) != institucion.id:
            self.stdout.write(
                self.style.WARNING('⚠ ADVERTENCIA: La institución activa no coincide con la membresía del usuario')
            )
