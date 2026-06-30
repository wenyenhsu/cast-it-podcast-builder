"""Workflow step executor."""

import logging
from typing import Any

from django.utils import timezone

from apps.workflow.models import WorkflowStepRun
from domain.workflow.dtos import StepExecutionResult
from domain.workflow.enums import WorkflowStatus
from domain.workflow.exceptions import WorkflowStateError, WorkflowStepError
from domain.workflow.state import assert_step_transition
from services.workflow.adapters.base import WorkflowStepAdapter
from services.workflow.adapters.registry import build_default_adapter_registry
from services.workflow.episode_sync import EpisodeWorkflowSync
from services.workflow.logging_utils import log_workflow_event

logger = logging.getLogger(__name__)


class WorkflowStepExecutor:
    """Executes a single workflow step through the adapter layer."""

    def __init__(
        self,
        adapters: dict[str, WorkflowStepAdapter] | None = None,
        episode_sync: EpisodeWorkflowSync | None = None,
    ) -> None:
        self._adapters = (
            adapters if adapters is not None else build_default_adapter_registry()
        )
        self._episode_sync = episode_sync or EpisodeWorkflowSync()

    def execute(
        self,
        step_run: WorkflowStepRun,
        *,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        """Validate, execute, and persist step run results."""
        adapter = self._adapters.get(step_run.workflow_step.step_type)
        if adapter is None:
            raise WorkflowStepError(
                f"No adapter registered for step type "
                f"'{step_run.workflow_step.step_type}'."
            )

        adapter.validate_input(step_run=step_run, context=context)
        if step_run.status in {WorkflowStatus.PENDING, WorkflowStatus.RETRYING}:
            self._transition_step(step_run, WorkflowStatus.RUNNING)
        elif step_run.status != WorkflowStatus.RUNNING:
            raise WorkflowStateError(
                f"Step run {step_run.id} cannot execute from status "
                f"'{step_run.status}'."
            )
        step_run.started_at = timezone.now()
        step_run.input_data = dict(context)
        step_run.save(
            update_fields=["status", "started_at", "input_data", "updated_at"]
        )

        self._episode_sync.on_step_started(
            step_run.workflow_run.episode,
            step_run.workflow_step.step_type,
        )

        log_workflow_event(
            "workflow_step_started",
            workflow_run_id=str(step_run.workflow_run_id),
            step_run_id=str(step_run.id),
            step_type=step_run.workflow_step.step_type,
            step_name=step_run.workflow_step.name,
        )

        try:
            result = adapter.execute(step_run=step_run, context=context)
        except Exception as exc:
            self._mark_failed(step_run, str(exc))
            raise WorkflowStepError(str(exc)) from exc

        self._mark_succeeded(step_run, result)
        return result

    def _mark_succeeded(
        self,
        step_run: WorkflowStepRun,
        result: StepExecutionResult,
    ) -> None:
        self._transition_step(step_run, WorkflowStatus.SUCCEEDED)
        step_run.output_data = result.output
        step_run.progress = result.progress
        step_run.completed_at = timezone.now()
        step_run.error_message = ""
        step_run.save(
            update_fields=[
                "status",
                "output_data",
                "progress",
                "completed_at",
                "error_message",
                "updated_at",
            ]
        )
        log_workflow_event(
            "workflow_step_succeeded",
            workflow_run_id=str(step_run.workflow_run_id),
            step_run_id=str(step_run.id),
            step_type=step_run.workflow_step.step_type,
        )

    def _mark_failed(self, step_run: WorkflowStepRun, message: str) -> None:
        self._transition_step(step_run, WorkflowStatus.FAILED)
        step_run.error_message = message
        step_run.completed_at = timezone.now()
        step_run.save(
            update_fields=["status", "error_message", "completed_at", "updated_at"]
        )
        log_workflow_event(
            "workflow_step_failed",
            workflow_run_id=str(step_run.workflow_run_id),
            step_run_id=str(step_run.id),
            step_type=step_run.workflow_step.step_type,
            error=message,
        )

    @staticmethod
    def _transition_step(step_run: WorkflowStepRun, new_status: str) -> None:
        assert_step_transition(step_run.status, new_status)
        step_run.status = new_status
