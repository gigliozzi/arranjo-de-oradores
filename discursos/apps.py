from django.apps import AppConfig


class DiscursosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "discursos"
    verbose_name = "Discursos"

    def ready(self):
        import discursos.signals  # noqa: F401
