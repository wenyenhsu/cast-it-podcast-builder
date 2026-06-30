"""Tests for workflow execution."""

import pytest

from domain.workflow.enums import WorkflowStatus, WorkflowStepType
from domain.workflow.exceptions import WorkflowStepError
from services.workflow.engine import WorkflowEngineService
from services.workflow.step_executor import WorkflowStepExecutor
from tests.services.workflow.conftest import MockStepAdapter


@pytest.mark.django_db
def test_execute_run_completes_all_steps(
    simple_definition,
    workflow_engine,
    mock_adapters,
) -> None:
    run = workflow_engine.create_run(simple_definition)
    result = workflow_engine.start_run(run)

    assert result.status == WorkflowStatus.SUCCEEDED
    assert result.progress == 100
    assert mock_adapters[WorkflowStepType.COLLECT_ARTICLES].call_count == 1
    assert mock_adapters[WorkflowStepType.PLAN_EPISODE].call_count == 1
    assert result.payload.get("episode_id") == "episode-123"


@pytest.mark.django_db
def test_step_failure_marks_workflow_failed(simple_definition) -> None:
    adapters = {
        WorkflowStepType.COLLECT_ARTICLES: MockStepAdapter(
            WorkflowStepType.COLLECT_ARTICLES,
            should_fail=True,
        ),
        WorkflowStepType.PLAN_EPISODE: MockStepAdapter(
            WorkflowStepType.PLAN_EPISODE,
        ),
    }
    engine = WorkflowEngineService(
        step_executor=WorkflowStepExecutor(adapters=adapters),
    )
    run = engine.create_run(simple_definition)
    result = engine.start_run(run)

    assert result.status == WorkflowStatus.FAILED
    assert "failed" in result.error_message.lower()


@pytest.mark.django_db
def test_step_retry_on_failure(simple_definition) -> None:
    failing = MockStepAdapter(
        WorkflowStepType.COLLECT_ARTICLES,
        should_fail=True,
    )
    adapters = {
        WorkflowStepType.COLLECT_ARTICLES: failing,
        WorkflowStepType.PLAN_EPISODE: MockStepAdapter(
            WorkflowStepType.PLAN_EPISODE,
            output={"episode_id": "ep-1"},
        ),
    }
    engine = WorkflowEngineService(
        step_executor=WorkflowStepExecutor(adapters=adapters),
    )
    run = engine.create_run(simple_definition)
    result = engine.start_run(run)
    assert failing.call_count == 2
    assert result.status == WorkflowStatus.FAILED


@pytest.mark.django_db
def test_step_executor_raises_for_unknown_adapter(simple_definition) -> None:
    run = WorkflowEngineService().create_run(simple_definition)
    step_run = run.step_runs.select_related("workflow_step").first()
    assert step_run is not None
    executor = WorkflowStepExecutor(adapters={})

    with pytest.raises(WorkflowStepError):
        executor.execute(step_run, context={})
