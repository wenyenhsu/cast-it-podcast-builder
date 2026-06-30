"""Tests for workflow retry operations."""

import pytest

from domain.workflow.enums import WorkflowStatus, WorkflowStepType
from domain.workflow.exceptions import WorkflowRetryError
from services.workflow.engine import WorkflowEngineService
from services.workflow.step_executor import WorkflowStepExecutor
from tests.services.workflow.conftest import MockStepAdapter


@pytest.mark.django_db
def test_retry_workflow_after_failure(simple_definition) -> None:
    plan_adapter = MockStepAdapter(
        WorkflowStepType.PLAN_EPISODE,
        output={"episode_id": "ep-retry"},
        should_fail=True,
    )
    adapters = {
        WorkflowStepType.COLLECT_ARTICLES: MockStepAdapter(
            WorkflowStepType.COLLECT_ARTICLES,
            output={"imported_count": 1},
        ),
        WorkflowStepType.PLAN_EPISODE: plan_adapter,
    }
    engine = WorkflowEngineService(
        step_executor=WorkflowStepExecutor(adapters=adapters),
    )
    run = engine.create_run(simple_definition)
    failed = engine.start_run(run)
    assert failed.status == WorkflowStatus.FAILED

    plan_adapter.should_fail = False
    retried = engine.retry_workflow(failed)
    assert retried.status == WorkflowStatus.SUCCEEDED


@pytest.mark.django_db
def test_retry_workflow_without_failed_steps_raises(
    simple_definition,
    workflow_engine,
) -> None:
    run = workflow_engine.create_run(simple_definition)
    completed = workflow_engine.start_run(run)
    with pytest.raises(WorkflowRetryError):
        workflow_engine.retry_workflow(completed)
