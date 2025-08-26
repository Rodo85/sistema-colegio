from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """
        Este método se ejecuta cuando la app se carga.
        Aquí registramos los signals.
        """
        try:
            import core.signals  # noqa
        except ImportError:
            pass
