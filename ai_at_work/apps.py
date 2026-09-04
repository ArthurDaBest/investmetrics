from django.apps import AppConfig


class AiAtWorkConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_at_work"
    verbose_name = "AI at Work"

    def ready(self):
        from . import signals  # noqa: F401
