"""Tests for workflow state transitions."""

import pytest

from domain.workflow.enums import WorkflowStatus
from domain.workflow.exceptions import WorkflowStateError
from domain.workflow.state import assert_step_transition, assert_workflow_transition


def test_valid_workflow_transitions() -> None:
    assert_workflow_transition(WorkflowStatus.PENDING, WorkflowStatus.QUEUED)
    assert_workflow_transition(WorkflowStatus.QUEUED, WorkflowStatus.RUNNING)
    assert_workflow_transition(WorkflowStatus.RUNNING, WorkflowStatus.SUCCEEDED)
    assert_workflow_transition(WorkflowStatus.RUNNING, WorkflowStatus.PAUSED)
    assert_workflow_transition(WorkflowStatus.PAUSED, WorkflowStatus.RUNNING)
    assert_workflow_transition(WorkflowStatus.FAILED, WorkflowStatus.RETRYING)


def test_invalid_workflow_transition_raises() -> None:
    with pytest.raises(WorkflowStateError):
        assert_workflow_transition(WorkflowStatus.SUCCEEDED, WorkflowStatus.RUNNING)


def test_valid_step_transitions() -> None:
    assert_step_transition(WorkflowStatus.PENDING, WorkflowStatus.RUNNING)
    assert_step_transition(WorkflowStatus.RUNNING, WorkflowStatus.SUCCEEDED)
    assert_step_transition(WorkflowStatus.FAILED, WorkflowStatus.SKIPPED)


def test_invalid_step_transition_raises() -> None:
    with pytest.raises(WorkflowStateError):
        assert_step_transition(WorkflowStatus.SUCCEEDED, WorkflowStatus.RUNNING)
