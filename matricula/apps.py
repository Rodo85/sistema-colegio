from django.apps import AppConfig


class MatriculaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'matricula'
    verbose_name = 'Matrícula'

    def ready(self):
        # Asegura la creación de permisos personalizados después de migrar
        from django.db.models.signals import post_migrate
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        def ensure_custom_permissions(sender, **kwargs):
            from .models import Estudiante
            try:
                ct = ContentType.objects.get_for_model(Estudiante)
                perms = [
                    ("access_consulta_estudiante", "Puede acceder a Consulta de Estudiante"),
                    ("print_ficha_estudiante", "Puede imprimir ficha del estudiante"),
                    ("print_comprobante_matricula", "Puede imprimir comprobante de matrícula"),
                ]
                for codename, name in perms:
                    Permission.objects.get_or_create(codename=codename, content_type=ct, defaults={"name": name})
            except Exception:
                # Evitar romper migraciones si el modelo aún no está listo
                pass

        post_migrate.connect(ensure_custom_permissions, sender=self)