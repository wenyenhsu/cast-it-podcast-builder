"""Workflow engine models."""

from django.db import models

from apps.core.models import DomainModel
from domain.workflow.enums import WorkflowStatus, WorkflowStepType


class WorkflowDefinition(DomainModel):
    """Named versioned workflow template."""

    name = models.CharField(max_length=100, db_index=True)
    version = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version"],
                name="unique_workflow_definition_version",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


class WorkflowStep(DomainModel):
    """One logical step in a workflow definition."""

    workflow_definition = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    name = models.CharField(max_length=100)
    sequence = models.PositiveIntegerField()
    step_type = models.CharField(
        max_length=40,
        choices=WorkflowStepType.choices,
        db_index=True,
    )
    timeout_seconds = models.PositiveIntegerField(default=3600)
    retry_limit = models.PositiveSmallIntegerField(default=3)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["workflow_definition", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow_definition", "sequence"],
                name="unique_workflow_step_sequence",
            ),
            models.UniqueConstraint(
                fields=["workflow_definition", "name"],
                name="unique_workflow_step_name",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.workflow_definition.name} — {self.name}"

    @property
    def is_optional(self) -> bool:
        return bool(self.config.get("optional", False))

    @property
    def is_enabled(self) -> bool:
        return bool(self.config.get("enabled", True))


class WorkflowRun(DomainModel):
    """One execution instance of a workflow definition."""

    workflow_definition = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.PROTECT,
        related_name="runs",
    )
    episode = models.ForeignKey(
        "episodes.Episode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_runs",
    )
    status = models.CharField(
        max_length=20,
        choices=WorkflowStatus.choices,
        default=WorkflowStatus.PENDING,
        db_index=True,
    )
    current_step = models.CharField(max_length=100, blank=True)
    progress = models.PositiveSmallIntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["workflow_definition", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(progress__gte=0) & models.Q(progress__lte=100),
                name="workflow_run_progress_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.workflow_definition} run ({self.status})"


class WorkflowStepRun(DomainModel):
    """Execution record for one step inside a workflow run."""

    workflow_run = models.ForeignKey(
        WorkflowRun,
        on_delete=models.CASCADE,
        related_name="step_runs",
    )
    workflow_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.PROTECT,
        related_name="step_runs",
    )
    status = models.CharField(
        max_length=20,
        choices=WorkflowStatus.choices,
        default=WorkflowStatus.PENDING,
        db_index=True,
    )
    progress = models.PositiveSmallIntegerField(default=0)
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["workflow_run", "workflow_step__sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow_run", "workflow_step"],
                name="unique_workflow_step_run",
            ),
            models.CheckConstraint(
                condition=models.Q(progress__gte=0) & models.Q(progress__lte=100),
                name="workflow_step_run_progress_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.workflow_step.name} ({self.status})"
