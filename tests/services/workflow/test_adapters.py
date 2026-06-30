"""Tests for workflow step adapters."""

from typing import Any

from domain.workflow.enums import WorkflowStepType
from services.workflow.adapters.implementations import (
    DefaultCollectArticlesAdapter,
    DefaultGenerateScriptAdapter,
    DefaultPlanEpisodeAdapter,
)
from services.workflow.adapters.registry import build_default_adapter_registry


class StubCollectPort:
    def collect(self, *, source_id: str | None) -> dict[str, Any]:
        return {"imported_count": 5, "source_id": source_id}


class StubPlanPort:
    def plan(self, *, language: str) -> dict[str, Any]:
        return {"episode_id": "episode-abc", "language": language}


class StubScriptPort:
    def generate(self, *, episode_id: str) -> dict[str, Any]:
        return {"script_id": "script-xyz", "episode_id": episode_id}


def test_collect_adapter_uses_port() -> None:
    adapter = DefaultCollectArticlesAdapter(port=StubCollectPort())
    result = adapter.execute(
        step_run=_FakeStepRun(),
        context={"source_id": "source-1"},
    )
    assert result.output["imported_count"] == 5


def test_plan_adapter_uses_port() -> None:
    adapter = DefaultPlanEpisodeAdapter(port=StubPlanPort())
    result = adapter.execute(
        step_run=_FakeStepRun(),
        context={"language": "en"},
    )
    assert result.output["episode_id"] == "episode-abc"


def test_script_adapter_requires_episode_id() -> None:
    adapter = DefaultGenerateScriptAdapter(port=StubScriptPort())
    result = adapter.execute(
        step_run=_FakeStepRun(),
        context={"episode_id": "episode-abc"},
    )
    assert result.output["script_id"] == "script-xyz"


def test_registry_contains_all_step_types() -> None:
    registry = build_default_adapter_registry()
    expected = {
        WorkflowStepType.INDEX_KNOWLEDGE,
        WorkflowStepType.COLLECT_ARTICLES,
        WorkflowStepType.SUMMARIZE_ARTICLES,
        WorkflowStepType.CLASSIFY_ARTICLES,
        WorkflowStepType.RANK_ARTICLES,
        WorkflowStepType.PLAN_EPISODE,
        WorkflowStepType.GENERATE_SCRIPT,
        WorkflowStepType.GENERATE_AUDIO,
        WorkflowStepType.PROCESS_AUDIO,
        WorkflowStepType.PUBLISH_EPISODE,
    }
    assert expected.issubset(set(registry.keys()))


class _FakeStepRun:
    input_data: dict[str, Any] = {}
