"""Tests for workflow definition and run creation."""

import pytest

from apps.workflow.models import WorkflowRun
from domain.workflow.enums import WorkflowStatus, WorkflowStepType
from domain.workflow.exceptions import WorkflowDefinitionError
from services.workflow.engine import WorkflowEngineService


@pytest.mark.django_db
def test_load_definition(workflow_definition) -> None:
    engine = WorkflowEngineService()
    loaded = engine.load_definition(name="podcast_production")
    assert loaded.name == "podcast_production"
    assert loaded.steps.count() == 10


@pytest.mark.django_db
def test_load_missing_definition_raises() -> None:
    engine = WorkflowEngineService()
    with pytest.raises(WorkflowDefinitionError):
        engine.load_definition(name="missing")


@pytest.mark.django_db
def test_create_run_creates_step_runs(simple_definition, workflow_engine) -> None:
    run = workflow_engine.create_run(simple_definition, payload={"language": "en"})
    assert WorkflowRun.objects.filter(pk=run.pk).exists()
    assert run.step_runs.count() == 2
    assert all(step.status == WorkflowStatus.PENDING for step in run.step_runs.all())


@pytest.mark.django_db
def test_default_definition_has_expected_steps(workflow_definition) -> None:
    step_types = list(
        workflow_definition.steps.order_by("sequence").values_list(
            "step_type",
            flat=True,
        )
    )
    assert step_types[0] == WorkflowStepType.INDEX_KNOWLEDGE
    assert WorkflowStepType.PUBLISH_EPISODE in step_types
