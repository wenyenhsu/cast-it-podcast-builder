"""Workflow application configuration."""

from django.apps import AppConfig


class WorkflowConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workflow"
    label = "workflow"
    verbose_name = "Workflow Engine"

    def ready(self) -> None:
        from django.db.models.signals import post_migrate

        from services.workflow.defaults import ensure_default_workflow_definition

        def _seed_workflow(**kwargs: object) -> None:
            ensure_default_workflow_definition()

        post_migrate.connect(
            _seed_workflow,
            dispatch_uid="workflow.ensure_default_definition",
        )
