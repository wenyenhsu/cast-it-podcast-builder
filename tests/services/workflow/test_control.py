"""Tests for pause, resume, cancel, and skip operations."""

import pytest

from domain.workflow.enums import WorkflowStatus, WorkflowStepType
from domain.workflow.exceptions import WorkflowCancellationError, WorkflowResumeError
from services.workflow.engine import WorkflowEngineService
from services.workflow.step_executor import WorkflowStepExecutor
from tests.services.workflow.conftest import MockStepAdapter


@pytest.mark.django_db
def test_pause_and_resume_workflow(simple_definition, workflow_engine) -> None:
    run = workflow_engine.create_run(simple_definition)
    workflow_engine._transition_run(run, WorkflowStatus.QUEUED)
    run.save(update_fields=["status", "updated_at"])
    workflow_engine._transition_run(run, WorkflowStatus.RUNNING)
    run.save(update_fields=["status", "updated_at"])

    paused = workflow_engine.pause_run(run)
    assert paused.status == WorkflowStatus.PAUSED

    resumed = workflow_engine.resume_run(paused)
    assert resumed.status == WorkflowStatus.SUCCEEDED


@pytest.mark.django_db
def test_resume_non_paused_raises(simple_definition, workflow_engine) -> None:
    run = workflow_engine.create_run(simple_definition)
    with pytest.raises(WorkflowResumeError):
        workflow_engine.resume_run(run)


@pytest.mark.django_db
def test_cancel_workflow(simple_definition, workflow_engine) -> None:
    run = workflow_engine.create_run(simple_definition)
    workflow_engine._transition_run(run, WorkflowStatus.QUEUED)
    run.save(update_fields=["status", "updated_at"])
    workflow_engine._transition_run(run, WorkflowStatus.RUNNING)
    run.save(update_fields=["status", "updated_at"])

    cancelled = workflow_engine.cancel_run(run)
    assert cancelled.status == WorkflowStatus.CANCELLED
    assert cancelled.completed_at is not None


@pytest.mark.django_db
def test_cancel_completed_raises(simple_definition, workflow_engine) -> None:
    run = workflow_engine.create_run(simple_definition)
    completed = workflow_engine.start_run(run)
    with pytest.raises(WorkflowCancellationError):
        workflow_engine.cancel_run(completed)


@pytest.mark.django_db
def test_skip_optional_step(db) -> None:
    from apps.workflow.models import WorkflowDefinition, WorkflowStep

    definition = WorkflowDefinition.objects.create(
        name="optional_step_workflow",
        version=1,
        is_active=True,
    )
    WorkflowStep.objects.create(
        workflow_definition=definition,
        name="Optional Index",
        sequence=1,
        step_type=WorkflowStepType.INDEX_KNOWLEDGE,
        config={"optional": True, "enabled": True},
    )
    adapters = {
        WorkflowStepType.INDEX_KNOWLEDGE: MockStepAdapter(
            WorkflowStepType.INDEX_KNOWLEDGE,
        ),
    }
    engine = WorkflowEngineService(
        step_executor=WorkflowStepExecutor(adapters=adapters),
    )
    run = engine.create_run(definition)
    step_run = run.step_runs.first()
    assert step_run is not None

    skipped = engine.skip_step(step_run)
    assert skipped.status == WorkflowStatus.SKIPPED

    result = engine.start_run(run)
    assert result.status == WorkflowStatus.SUCCEEDED
