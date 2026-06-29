"""Job orchestration exceptions."""


class JobOrchestrationError(Exception):
    """Base exception for job orchestration operations."""


class JobCreationError(JobOrchestrationError):
    """Raised when a job record cannot be created."""


class JobUpdateError(JobOrchestrationError):
    """Raised when a job record cannot be updated."""


class JobExecutionError(JobOrchestrationError):
    """Base exception for job execution failures."""


class JobPermanentError(JobExecutionError):
    """Raised for non-retryable job execution failures."""


class JobTransientError(JobExecutionError):
    """Raised for retryable job execution failures."""


class JobRetryError(JobOrchestrationError):
    """Raised when a job retry operation fails."""


class JobCancellationError(JobOrchestrationError):
    """Raised when a job cancellation operation fails."""


class SchedulerConfigurationError(JobOrchestrationError):
    """Raised when scheduler configuration is invalid."""
