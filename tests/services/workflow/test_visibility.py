"""Tests for workflow visibility and progress."""

import pytest

from domain.workflow.enums import WorkflowStatus
from services.workflow.engine import WorkflowEngineService
from services.workflow.visibility import WorkflowVisibilityService


@pytest.mark.django_db
def test_progress_calculation(simple_definition, workflow_engine) -> None:
    run = workflow_engine.create_run(simple_definition)
    workflow_engine.start_run(run)

    progress = WorkflowVisibilityService().get_progress(run)
    assert progress.total_step_count == 2
    assert progress.completed_step_count == 2
    assert progress.progress_percentage == 100
    assert progress.last_successful_step == "Plan"


@pytest.mark.django_db
def test_progress_after_partial_failure(simple_definition) -> None:
    from domain.workflow.enums import WorkflowStepType
    from services.workflow.step_executor import WorkflowStepExecutor
    from tests.services.workflow.conftest import MockStepAdapter

    adapters = {
        WorkflowStepType.COLLECT_ARTICLES: MockStepAdapter(
            WorkflowStepType.COLLECT_ARTICLES,
            output={"imported_count": 1},
        ),
        WorkflowStepType.PLAN_EPISODE: MockStepAdapter(
            WorkflowStepType.PLAN_EPISODE,
            should_fail=True,
        ),
    }
    engine = WorkflowEngineService(
        step_executor=WorkflowStepExecutor(adapters=adapters),
    )
    run = engine.create_run(simple_definition)
    engine.start_run(run)

    progress = engine.get_progress(run)
    assert progress.completed_step_count == 1
    assert progress.failed_step_count == 1
    assert progress.status == WorkflowStatus.FAILED
    assert progress.last_error
