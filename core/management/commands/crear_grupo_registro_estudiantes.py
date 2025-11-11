from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Crear grupo "Registro de Estudiantes" con permisos para crear estudiantes pero solo ver mediante búsqueda'

    def handle(self, *args, **options):
        self.stdout.write('Creando grupo "Registro de Estudiantes"...')
        self.stdout.write('=' * 60)
        
        # Crear o obtener el grupo
        grupo, created = Group.objects.get_or_create(name='Registro de Estudiantes')
        
        if created:
            self.stdout.write(self.style.SUCCESS('Grupo creado exitosamente'))
        else:
            self.stdout.write(self.style.WARNING('El grupo ya existia, actualizando permisos...'))
        
        # Limpiar permisos existentes
        grupo.permissions.clear()
        
        # Obtener el content type de Estudiante
        from matricula.models import Estudiante, PersonaContacto, EncargadoEstudiante
        
        estudiante_ct = ContentType.objects.get_for_model(Estudiante)
        contacto_ct = ContentType.objects.get_for_model(PersonaContacto)
        relacion_ct = ContentType.objects.get_for_model(EncargadoEstudiante)
        
        permisos_a_agregar = []
        
        # Permisos de Estudiante
        # - Crear estudiantes (add)
        # - Ver estudiantes (view)
        # - Cambiar estudiantes (change) - necesario para editar
        # - Permiso personalizado: only_search_estudiante
        permisos_estudiante = [
            'add_estudiante',
            'view_estudiante',
            'change_estudiante',
            'only_search_estudiante',  # Permiso personalizado
        ]
        
        for codename in permisos_estudiante:
            try:
                perm = Permission.objects.get(
                    codename=codename,
                    content_type=estudiante_ct
                )
                permisos_a_agregar.append(perm)
                self.stdout.write(f'  [OK] Permiso agregado: {perm.name}')
            except Permission.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'  [ERROR] Permiso no encontrado: {codename}'))
        
        # Permisos para PersonaContacto (encargados)
        permisos_contacto = [
            'add_personacontacto',
            'view_personacontacto',
            'change_personacontacto',
            'only_search_personacontacto',
        ]
        
        for codename in permisos_contacto:
            try:
                perm = Permission.objects.get(
                    codename=codename,
                    content_type=contacto_ct
                )
                permisos_a_agregar.append(perm)
                self.stdout.write(f'  [OK] Permiso agregado: {perm.name}')
            except Permission.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  [WARN] Permiso no encontrado: {codename}'))
        
        # Permisos para EncargadoEstudiante
        permisos_relacion = [
            'add_encargadoestudiante',
            'view_encargadoestudiante',
            'change_encargadoestudiante',
        ]
        
        for codename in permisos_relacion:
            try:
                perm = Permission.objects.get(
                    codename=codename,
                    content_type=relacion_ct
                )
                permisos_a_agregar.append(perm)
                self.stdout.write(f'  [OK] Permiso agregado: {perm.name}')
            except Permission.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  [WARN] Permiso no encontrado: {codename}'))
        
        # Agregar todos los permisos al grupo
        grupo.permissions.set(permisos_a_agregar)
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('GRUPO CREADO/ACTUALIZADO EXITOSAMENTE'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write('Resumen:')
        self.stdout.write(f'  - Nombre del grupo: {grupo.name}')
        self.stdout.write(f'  - Total de permisos: {grupo.permissions.count()}')
        self.stdout.write('')
        self.stdout.write('Comportamiento:')
        self.stdout.write('  - Puede crear y editar estudiantes')
        self.stdout.write('  - Al entrar a la lista de estudiantes, NO vera ningun registro')
        self.stdout.write('  - Solo vera resultados cuando use el campo de busqueda')
        self.stdout.write('  - Puede gestionar encargados (contactos)')
        self.stdout.write('')
        self.stdout.write('Para asignar este grupo a un usuario:')
        self.stdout.write('  1. Ve al admin de Django')
        self.stdout.write('  2. Edita el usuario deseado')
        self.stdout.write('  3. En la seccion "Permisos", agrega el grupo "Registro de Estudiantes"')
        self.stdout.write('  4. Guarda los cambios')
        self.stdout.write('')

