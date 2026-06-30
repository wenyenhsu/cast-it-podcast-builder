"""Workflow domain exceptions."""


class WorkflowError(Exception):
    """Base exception for workflow operations."""


class WorkflowDefinitionError(WorkflowError):
    """Raised when a workflow definition is invalid or missing."""


class WorkflowRunError(WorkflowError):
    """Raised when a workflow run operation fails."""


class WorkflowStepError(WorkflowError):
    """Raised when a workflow step execution fails."""


class WorkflowStateError(WorkflowError):
    """Raised when an invalid workflow state transition is attempted."""


class WorkflowRetryError(WorkflowError):
    """Raised when a workflow retry operation fails."""


class WorkflowResumeError(WorkflowError):
    """Raised when a workflow resume operation fails."""


class WorkflowCancellationError(WorkflowError):
    """Raised when a workflow cancellation operation fails."""
