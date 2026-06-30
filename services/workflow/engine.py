"""Workflow engine orchestration service."""

import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.episodes.models import Episode
from apps.workflow.models import (
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStepRun,
)
from domain.workflow.enums import WorkflowStatus
from domain.workflow.exceptions import (
    WorkflowCancellationError,
    WorkflowDefinitionError,
    WorkflowResumeError,
    WorkflowRetryError,
    WorkflowRunError,
)
from domain.workflow.state import assert_workflow_transition
from services.workflow.episode_sync import EpisodeWorkflowSync
from services.workflow.logging_utils import log_workflow_event
from services.workflow.step_executor import WorkflowStepExecutor
from services.workflow.visibility import WorkflowVisibilityService


class WorkflowEngineService:
    """Orchestrates workflow runs, step execution, and state transitions."""

    def __init__(
        self,
        step_executor: WorkflowStepExecutor | None = None,
        visibility: WorkflowVisibilityService | None = None,
        episode_sync: EpisodeWorkflowSync | None = None,
    ) -> None:
        self._executor = step_executor or WorkflowStepExecutor()
        self._visibility = visibility or WorkflowVisibilityService()
        self._episode_sync = episode_sync or EpisodeWorkflowSync()

    def load_definition(
        self,
        *,
        name: str,
        version: int | None = None,
    ) -> WorkflowDefinition:
        queryset = WorkflowDefinition.objects.filter(name=name, is_active=True)
        if version is not None:
            definition = queryset.filter(version=version).first()
        else:
            definition = queryset.order_by("-version").first()
        if definition is None:
            raise WorkflowDefinitionError(
                f"Workflow definition '{name}' version {version} not found."
            )
        return definition

    @transaction.atomic
    def create_run(
        self,
        definition: WorkflowDefinition,
        *,
        episode_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        episode = None
        if episode_id:
            episode = Episode.objects.get(pk=episode_id)

        run = WorkflowRun.objects.create(
            workflow_definition=definition,
            episode=episode,
            status=WorkflowStatus.PENDING,
            payload=payload or {},
        )

        enabled_steps = [
            step
            for step in definition.steps.order_by("sequence")
            if step.config.get("enabled", True) is not False
        ]

        for step in enabled_steps:
            WorkflowStepRun.objects.create(
                workflow_run=run,
                workflow_step=step,
                status=WorkflowStatus.PENDING,
            )

        log_workflow_event(
            "workflow_created",
            workflow_run_id=str(run.id),
            definition_name=definition.name,
            definition_version=definition.version,
        )
        return run

    def start_run(self, run: WorkflowRun) -> WorkflowRun:
        self._transition_run(run, WorkflowStatus.QUEUED)
        run.save(update_fields=["status", "updated_at"])
        self._transition_run(run, WorkflowStatus.RUNNING)
        run.started_at = timezone.now()
        run.save(update_fields=["status", "started_at", "updated_at"])
        log_workflow_event("workflow_started", workflow_run_id=str(run.id))
        return self.execute_run(run)

    def execute_run(self, run: WorkflowRun) -> WorkflowRun:
        """Execute all pending steps synchronously until completion or failure."""
        if run.status not in {
            WorkflowStatus.RUNNING,
            WorkflowStatus.QUEUED,
            WorkflowStatus.RETRYING,
        }:
            self._transition_run(run, WorkflowStatus.RUNNING)
            run.save(update_fields=["status", "updated_at"])

        context = self._build_context(run)

        while True:
            if run.status in {WorkflowStatus.PAUSED, WorkflowStatus.CANCELLED}:
                break

            pending_steps = self._iter_executable_steps(run)
            if not pending_steps:
                break

            step_run = pending_steps[0]

            run.current_step = step_run.workflow_step.name
            run.save(update_fields=["current_step", "updated_at"])

            if not step_run.workflow_step.is_enabled:
                self._skip_step(step_run)
                continue

            try:
                result = self._executor.execute(step_run, context=context)
            except Exception as exc:
                run.error_message = str(exc)
                run.save(update_fields=["error_message", "updated_at"])
                if self._can_retry_step(step_run):
                    step_run.retry_count += 1
                    self._transition_step_run(step_run, WorkflowStatus.RETRYING)
                    step_run.error_message = ""
                    step_run.completed_at = None
                    step_run.progress = 0
                    step_run.save(
                        update_fields=[
                            "retry_count",
                            "status",
                            "error_message",
                            "completed_at",
                            "progress",
                            "updated_at",
                        ]
                    )
                    log_workflow_event(
                        "workflow_retried",
                        workflow_run_id=str(run.id),
                        step_run_id=str(step_run.id),
                        retry_count=step_run.retry_count,
                    )
                    continue
                self._fail_run(run, str(exc))
                return run

            context = self._merge_context(context, result.output)
            run.payload = context
            self._maybe_attach_episode(run, context)
            run.result = {"last_step_output": result.output, "context": context}
            run.save(update_fields=["payload", "result", "episode_id", "updated_at"])
            self._visibility.refresh_run_progress(run)

        if run.status == WorkflowStatus.RUNNING:
            self._complete_run(run)
        return run

    def retry_step(self, step_run: WorkflowStepRun) -> WorkflowStepRun:
        if step_run.status != WorkflowStatus.FAILED:
            raise WorkflowRetryError(
                f"Step run {step_run.id} cannot be retried from status "
                f"'{step_run.status}'."
            )
        if step_run.retry_count >= step_run.workflow_step.retry_limit:
            raise WorkflowRetryError(
                f"Step run {step_run.id} exceeded retry limit "
                f"({step_run.workflow_step.retry_limit})."
            )

        self._transition_step_run(step_run, WorkflowStatus.RETRYING)
        step_run.retry_count += 1
        step_run.error_message = ""
        step_run.completed_at = None
        step_run.output_data = {}
        step_run.progress = 0
        step_run.save(
            update_fields=[
                "status",
                "retry_count",
                "error_message",
                "completed_at",
                "output_data",
                "progress",
                "updated_at",
            ]
        )

        run = step_run.workflow_run
        self._transition_run(run, WorkflowStatus.RETRYING)
        run.retry_count += 1
        run.error_message = ""
        run.save(update_fields=["status", "retry_count", "error_message", "updated_at"])

        log_workflow_event(
            "workflow_retried",
            workflow_run_id=str(run.id),
            step_run_id=str(step_run.id),
            retry_count=step_run.retry_count,
        )

        self._transition_run(run, WorkflowStatus.RUNNING)
        run.save(update_fields=["status", "updated_at"])
        self.execute_run(run)
        step_run.refresh_from_db()
        return step_run

    def retry_workflow(self, run: WorkflowRun) -> WorkflowRun:
        failed_steps = run.step_runs.filter(status=WorkflowStatus.FAILED).order_by(
            "workflow_step__sequence"
        )
        if not failed_steps.exists():
            raise WorkflowRetryError(f"Workflow run {run.id} has no failed steps.")

        self._transition_run(run, WorkflowStatus.RETRYING)
        run.error_message = ""
        run.save(update_fields=["status", "error_message", "updated_at"])
        log_workflow_event("workflow_retried", workflow_run_id=str(run.id))

        for step_run in failed_steps:
            step_run.status = WorkflowStatus.PENDING
            step_run.error_message = ""
            step_run.completed_at = None
            step_run.save(
                update_fields=["status", "error_message", "completed_at", "updated_at"]
            )

        self._transition_run(run, WorkflowStatus.RUNNING)
        run.save(update_fields=["status", "updated_at"])
        return self.execute_run(run)

    def pause_run(self, run: WorkflowRun) -> WorkflowRun:
        if run.status != WorkflowStatus.RUNNING:
            raise WorkflowRunError(
                f"Workflow run {run.id} cannot be paused from status '{run.status}'."
            )
        self._transition_run(run, WorkflowStatus.PAUSED)
        run.save(update_fields=["status", "updated_at"])
        log_workflow_event("workflow_paused", workflow_run_id=str(run.id))
        return run

    def resume_run(self, run: WorkflowRun) -> WorkflowRun:
        if run.status != WorkflowStatus.PAUSED:
            raise WorkflowResumeError(
                f"Workflow run {run.id} cannot be resumed from status '{run.status}'."
            )
        self._transition_run(run, WorkflowStatus.RUNNING)
        run.save(update_fields=["status", "updated_at"])
        log_workflow_event("workflow_resumed", workflow_run_id=str(run.id))
        return self.execute_run(run)

    def cancel_run(self, run: WorkflowRun) -> WorkflowRun:
        if run.status in {WorkflowStatus.SUCCEEDED, WorkflowStatus.CANCELLED}:
            raise WorkflowCancellationError(
                f"Workflow run {run.id} cannot be cancelled from status '{run.status}'."
            )
        self._transition_run(run, WorkflowStatus.CANCELLED)
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "completed_at", "updated_at"])

        run.step_runs.filter(
            status__in=[
                WorkflowStatus.PENDING,
                WorkflowStatus.QUEUED,
                WorkflowStatus.RUNNING,
                WorkflowStatus.RETRYING,
                WorkflowStatus.PAUSED,
            ]
        ).update(status=WorkflowStatus.CANCELLED)

        log_workflow_event("workflow_cancelled", workflow_run_id=str(run.id))
        return run

    def skip_step(self, step_run: WorkflowStepRun) -> WorkflowStepRun:
        if not step_run.workflow_step.is_optional:
            raise WorkflowRunError(
                f"Step '{step_run.workflow_step.name}' is required "
                "and cannot be skipped."
            )
        if step_run.status not in {WorkflowStatus.PENDING, WorkflowStatus.FAILED}:
            raise WorkflowRunError(
                f"Step run {step_run.id} cannot be skipped from status "
                f"'{step_run.status}'."
            )
        self._skip_step(step_run)
        return step_run

    def get_progress(self, run: WorkflowRun) -> Any:
        return self._visibility.get_progress(run)

    def _complete_run(self, run: WorkflowRun) -> None:
        pending = run.step_runs.exclude(
            status__in=[
                WorkflowStatus.SUCCEEDED,
                WorkflowStatus.SKIPPED,
                WorkflowStatus.CANCELLED,
            ]
        )
        if pending.exists():
            return

        self._transition_run(run, WorkflowStatus.SUCCEEDED)
        run.completed_at = timezone.now()
        run.progress = 100
        run.error_message = ""
        run.save(
            update_fields=[
                "status",
                "completed_at",
                "progress",
                "error_message",
                "updated_at",
            ]
        )
        self._episode_sync.on_workflow_succeeded(run.episode)
        log_workflow_event("workflow_succeeded", workflow_run_id=str(run.id))

    def _fail_run(self, run: WorkflowRun, message: str) -> None:
        self._transition_run(run, WorkflowStatus.FAILED)
        run.error_message = message
        run.completed_at = timezone.now()
        run.save(
            update_fields=["status", "error_message", "completed_at", "updated_at"]
        )
        self._episode_sync.on_workflow_failed(run.episode)
        log_workflow_event(
            "workflow_failed",
            workflow_run_id=str(run.id),
            error=message,
        )

    def _skip_step(self, step_run: WorkflowStepRun) -> None:
        self._transition_step_run(step_run, WorkflowStatus.SKIPPED)
        step_run.completed_at = timezone.now()
        step_run.save(update_fields=["status", "completed_at", "updated_at"])
        log_workflow_event(
            "workflow_step_skipped",
            workflow_run_id=str(step_run.workflow_run_id),
            step_run_id=str(step_run.id),
        )

    def _can_retry_step(self, step_run: WorkflowStepRun) -> bool:
        return step_run.retry_count < step_run.workflow_step.retry_limit

    def _iter_executable_steps(self, run: WorkflowRun) -> list[WorkflowStepRun]:
        return list(
            run.step_runs.select_related("workflow_step")
            .filter(
                status__in=[
                    WorkflowStatus.PENDING,
                    WorkflowStatus.QUEUED,
                    WorkflowStatus.RETRYING,
                ]
            )
            .order_by("workflow_step__sequence")
        )

    @staticmethod
    def _maybe_attach_episode(run: WorkflowRun, context: dict[str, Any]) -> None:
        if run.episode_id is not None:
            return
        episode_id = context.get("episode_id")
        if not episode_id:
            return
        try:
            episode_uuid = uuid.UUID(str(episode_id))
        except ValueError:
            return
        if Episode.objects.filter(pk=episode_uuid).exists():
            run.episode_id = episode_uuid

    @staticmethod
    def _build_context(run: WorkflowRun) -> dict[str, Any]:
        context = dict(run.payload or {})
        if run.episode_id and "episode_id" not in context:
            context["episode_id"] = str(run.episode_id)
        for step_run in run.step_runs.filter(
            status=WorkflowStatus.SUCCEEDED
        ).select_related("workflow_step"):
            context.update(step_run.output_data or {})
        return context

    @staticmethod
    def _merge_context(
        context: dict[str, Any],
        output: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(context)
        merged.update(output)
        return merged

    @staticmethod
    def _transition_run(run: WorkflowRun, new_status: str) -> None:
        previous = run.status
        assert_workflow_transition(previous, new_status)
        run.status = new_status
        log_workflow_event(
            "workflow_state_transition",
            workflow_run_id=str(run.id),
            from_status=previous,
            to_status=new_status,
        )

    @staticmethod
    def _transition_step_run(step_run: WorkflowStepRun, new_status: str) -> None:
        from domain.workflow.state import assert_step_transition

        assert_step_transition(step_run.status, new_status)
        step_run.status = new_status
