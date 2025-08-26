from django.core.management.base import BaseCommand
from matricula.models import Estudiante

class Command(BaseCommand):
    help = 'Debug del modelo Estudiante para ver sus campos'

    def handle(self, *args, **options):
        self.stdout.write('=== DEBUG DEL MODELO ESTUDIANTE ===')
        
        # Verificar campos del modelo
        self.stdout.write(f'\nCampos del modelo:')
        for field in Estudiante._meta.fields:
            self.stdout.write(f'  - {field.name}: {type(field).__name__}')
        
        # Verificar si tiene campo institución
        if hasattr(Estudiante._meta, 'get_field'):
            try:
                institucion_field = Estudiante._meta.get_field('institucion')
                self.stdout.write(f'\n✓ Campo institución encontrado:')
                self.stdout.write(f'  - Tipo: {type(institucion_field).__name__}')
                self.stdout.write(f'  - Null: {institucion_field.null}')
                self.stdout.write(f'  - Blank: {institucion_field.blank}')
                self.stdout.write(f'  - Related model: {institucion_field.related_model}')
            except Exception as e:
                self.stdout.write(f'\n✗ Error obteniendo campo institución: {e}')
        
        # Verificar si tiene campo institución_id
        if hasattr(Estudiante._meta, 'get_field'):
            try:
                institucion_id_field = Estudiante._meta.get_field('institucion_id')
                self.stdout.write(f'\n✓ Campo institución_id encontrado:')
                self.stdout.write(f'  - Tipo: {type(institucion_id_field).__name__}')
            except Exception as e:
                self.stdout.write(f'\n✗ Campo institución_id no encontrado: {e}')
        
        # Verificar atributos del modelo
        self.stdout.write(f'\nAtributos del modelo:')
        self.stdout.write(f'  - __name__: {Estudiante.__name__}')
        self.stdout.write(f'  - _meta.app_label: {Estudiante._meta.app_label}')
        self.stdout.write(f'  - _meta.model_name: {Estudiante._meta.model_name}')
        
        # Verificar si el modelo está registrado en admin
        try:
            from django.contrib import admin
            admin_site = admin.site
            if Estudiante in admin_site._registry:
                self.stdout.write(f'\n✓ Modelo registrado en admin')
                admin_class = admin_site._registry[Estudiante]
                self.stdout.write(f'  - Clase admin: {type(admin_class).__name__}')
                self.stdout.write(f'  - Mixins: {[base.__name__ for base in type(admin_class).__bases__]}')
            else:
                self.stdout.write(f'\n✗ Modelo NO registrado en admin')
        except Exception as e:
            self.stdout.write(f'\n✗ Error verificando admin: {e}')
