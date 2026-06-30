"""Workflow state transition rules."""

from domain.workflow.enums import WorkflowStatus
from domain.workflow.exceptions import WorkflowStateError

WORKFLOW_TRANSITIONS: dict[str, set[str]] = {
    WorkflowStatus.PENDING: {WorkflowStatus.QUEUED, WorkflowStatus.CANCELLED},
    WorkflowStatus.QUEUED: {WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED},
    WorkflowStatus.RUNNING: {
        WorkflowStatus.SUCCEEDED,
        WorkflowStatus.FAILED,
        WorkflowStatus.PAUSED,
        WorkflowStatus.CANCELLED,
        WorkflowStatus.RETRYING,
    },
    WorkflowStatus.PAUSED: {WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED},
    WorkflowStatus.FAILED: {WorkflowStatus.RETRYING, WorkflowStatus.CANCELLED},
    WorkflowStatus.RETRYING: {
        WorkflowStatus.RUNNING,
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
    },
    WorkflowStatus.SUCCEEDED: set(),
    WorkflowStatus.CANCELLED: set(),
    WorkflowStatus.SKIPPED: set(),
}

STEP_TRANSITIONS: dict[str, set[str]] = {
    WorkflowStatus.PENDING: {
        WorkflowStatus.QUEUED,
        WorkflowStatus.RUNNING,
        WorkflowStatus.SKIPPED,
        WorkflowStatus.CANCELLED,
    },
    WorkflowStatus.QUEUED: {WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED},
    WorkflowStatus.RUNNING: {
        WorkflowStatus.SUCCEEDED,
        WorkflowStatus.FAILED,
        WorkflowStatus.PAUSED,
        WorkflowStatus.CANCELLED,
        WorkflowStatus.RETRYING,
    },
    WorkflowStatus.PAUSED: {WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED},
    WorkflowStatus.FAILED: {
        WorkflowStatus.RETRYING,
        WorkflowStatus.SKIPPED,
        WorkflowStatus.CANCELLED,
    },
    WorkflowStatus.RETRYING: {
        WorkflowStatus.RUNNING,
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
    },
    WorkflowStatus.SUCCEEDED: set(),
    WorkflowStatus.CANCELLED: set(),
    WorkflowStatus.SKIPPED: set(),
}


def assert_workflow_transition(current: str, new: str) -> None:
    """Validate a workflow run state transition."""
    allowed = WORKFLOW_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise WorkflowStateError(
            f"Invalid workflow transition from '{current}' to '{new}'."
        )


def assert_step_transition(current: str, new: str) -> None:
    """Validate a workflow step run state transition."""
    allowed = STEP_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise WorkflowStateError(
            f"Invalid step transition from '{current}' to '{new}'."
        )
