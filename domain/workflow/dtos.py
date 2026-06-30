"""Workflow domain data transfer objects."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StepExecutionResult:
    """Normalized output from a workflow step execution."""

    output: dict[str, Any]
    progress: int = 100


@dataclass(frozen=True)
class WorkflowProgress:
    """Computed visibility information for a workflow run."""

    workflow_run_id: str
    status: str
    current_step: str
    completed_step_count: int
    failed_step_count: int
    skipped_step_count: int
    total_step_count: int
    progress_percentage: int
    last_error: str
    last_successful_step: str
    step_details: list[dict[str, Any]] = field(default_factory=list)
