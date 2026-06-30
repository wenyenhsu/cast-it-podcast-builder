"""Core application configuration."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
    verbose_name = "Core"

    def ready(self) -> None:
        from django.contrib import admin
        from django.db.models.signals import post_migrate

        from apps.core.admin.site import patch_admin_site
        from services.admin.permissions import ensure_admin_roles

        patch_admin_site(admin.site)

        def _create_admin_roles(**kwargs: object) -> None:
            ensure_admin_roles()

        post_migrate.connect(
            _create_admin_roles, dispatch_uid="core.ensure_admin_roles"
        )
