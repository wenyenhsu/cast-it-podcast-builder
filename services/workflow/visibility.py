"""Workflow progress and visibility calculations."""

from typing import Any

from apps.workflow.models import WorkflowRun, WorkflowStepRun
from domain.workflow.dtos import WorkflowProgress
from domain.workflow.enums import WorkflowStatus


class WorkflowVisibilityService:
    """Computes pipeline visibility for workflow runs."""

    def get_progress(self, workflow_run: WorkflowRun) -> WorkflowProgress:
        step_runs = list(
            workflow_run.step_runs.select_related("workflow_step").order_by(
                "workflow_step__sequence"
            )
        )
        total = len(step_runs)
        completed = sum(
            1 for step in step_runs if step.status == WorkflowStatus.SUCCEEDED
        )
        failed = sum(1 for step in step_runs if step.status == WorkflowStatus.FAILED)
        skipped = sum(1 for step in step_runs if step.status == WorkflowStatus.SKIPPED)

        progress_pct = int((completed / total) * 100) if total else 0
        last_success = ""
        for step in step_runs:
            if step.status == WorkflowStatus.SUCCEEDED:
                last_success = step.workflow_step.name

        return WorkflowProgress(
            workflow_run_id=str(workflow_run.id),
            status=workflow_run.status,
            current_step=workflow_run.current_step,
            completed_step_count=completed,
            failed_step_count=failed,
            skipped_step_count=skipped,
            total_step_count=total,
            progress_percentage=progress_pct,
            last_error=workflow_run.error_message,
            last_successful_step=last_success,
            step_details=[self._step_detail(step) for step in step_runs],
        )

    def refresh_run_progress(self, workflow_run: WorkflowRun) -> WorkflowRun:
        progress = self.get_progress(workflow_run)
        workflow_run.progress = progress.progress_percentage
        workflow_run.save(update_fields=["progress", "updated_at"])
        return workflow_run

    @staticmethod
    def _step_detail(step_run: WorkflowStepRun) -> dict[str, Any]:
        return {
            "step_run_id": str(step_run.id),
            "step_name": step_run.workflow_step.name,
            "step_type": step_run.workflow_step.step_type,
            "status": step_run.status,
            "progress": step_run.progress,
            "retry_count": step_run.retry_count,
            "error_message": step_run.error_message,
            "started_at": step_run.started_at,
            "completed_at": step_run.completed_at,
        }
