"""Publish application configuration."""

from django.apps import AppConfig


class PublishConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.publish"
    label = "publish"
    verbose_name = "Publish"
