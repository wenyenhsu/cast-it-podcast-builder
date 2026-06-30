"""Base workflow step adapter."""

from abc import ABC, abstractmethod
from typing import Any

from apps.workflow.models import WorkflowStepRun
from domain.workflow.dtos import StepExecutionResult
from domain.workflow.exceptions import WorkflowStepError


class WorkflowStepAdapter(ABC):
    """Translates workflow step input into business service calls."""

    step_type: str

    @abstractmethod
    def execute(
        self,
        *,
        step_run: WorkflowStepRun,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        """Execute the step and return normalized output."""

    def validate_input(
        self,
        *,
        step_run: WorkflowStepRun,
        context: dict[str, Any],
    ) -> None:
        """Validate step input before execution."""
        return None

    def _require_key(self, context: dict[str, Any], key: str) -> Any:
        value = context.get(key)
        if value is None:
            raise WorkflowStepError(f"Missing required context key: {key}")
        return value
