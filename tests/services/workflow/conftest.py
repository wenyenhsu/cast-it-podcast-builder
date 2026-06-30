"""Shared fixtures for workflow tests."""

from typing import Any

import pytest

from apps.workflow.models import WorkflowDefinition, WorkflowStep
from domain.workflow.dtos import StepExecutionResult
from domain.workflow.enums import WorkflowStepType
from services.workflow.adapters.base import WorkflowStepAdapter
from services.workflow.defaults import ensure_default_workflow_definition
from services.workflow.engine import WorkflowEngineService
from services.workflow.step_executor import WorkflowStepExecutor


class MockStepAdapter(WorkflowStepAdapter):
    """Configurable mock adapter for workflow tests."""

    def __init__(
        self,
        step_type: str,
        *,
        output: dict[str, Any] | None = None,
        should_fail: bool = False,
    ) -> None:
        self.step_type = step_type
        self.output = output or {"status": "ok"}
        self.should_fail = should_fail
        self.call_count = 0

    def execute(
        self,
        *,
        step_run: Any,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError(f"Step {self.step_type} failed.")
        merged = dict(self.output)
        merged.update({"step_type": self.step_type})
        return StepExecutionResult(output=merged)


@pytest.fixture
def workflow_definition(db: None) -> WorkflowDefinition:
    return ensure_default_workflow_definition()


@pytest.fixture
def simple_definition(db: None) -> WorkflowDefinition:
    definition = WorkflowDefinition.objects.create(
        name="test_workflow",
        version=1,
        description="Test workflow",
        is_active=True,
    )
    WorkflowStep.objects.create(
        workflow_definition=definition,
        name="Collect",
        sequence=1,
        step_type=WorkflowStepType.COLLECT_ARTICLES,
        retry_limit=1,
        config={"enabled": True},
    )
    WorkflowStep.objects.create(
        workflow_definition=definition,
        name="Plan",
        sequence=2,
        step_type=WorkflowStepType.PLAN_EPISODE,
        retry_limit=1,
        config={"enabled": True},
    )
    return definition


@pytest.fixture
def mock_adapters() -> dict[str, MockStepAdapter]:
    return {
        WorkflowStepType.COLLECT_ARTICLES: MockStepAdapter(
            WorkflowStepType.COLLECT_ARTICLES,
            output={"imported_count": 3},
        ),
        WorkflowStepType.PLAN_EPISODE: MockStepAdapter(
            WorkflowStepType.PLAN_EPISODE,
            output={"episode_id": "episode-123"},
        ),
        WorkflowStepType.GENERATE_SCRIPT: MockStepAdapter(
            WorkflowStepType.GENERATE_SCRIPT,
            output={"script_id": "script-456", "episode_id": "episode-123"},
        ),
    }


@pytest.fixture
def workflow_engine(mock_adapters: dict[str, MockStepAdapter]) -> WorkflowEngineService:
    executor = WorkflowStepExecutor(adapters=mock_adapters)
    return WorkflowEngineService(step_executor=executor)
