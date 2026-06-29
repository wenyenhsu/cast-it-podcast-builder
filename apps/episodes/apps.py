"""Episodes application configuration."""

from django.apps import AppConfig


class EpisodesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.episodes"
    label = "episodes"
    verbose_name = "Episodes"
