"""Tests for script versioning."""

import pytest

from apps.scripts.models import Script, ScriptMetadata, ScriptStatus
from domain.scripts.exceptions import ScriptVersionConflictError
from services.scripts.version_service import ScriptVersionService


@pytest.fixture
def version_service() -> ScriptVersionService:
    return ScriptVersionService()


def test_get_next_version_starts_at_one(
    version_service: ScriptVersionService,
    sample_episode: object,
) -> None:
    assert version_service.get_next_version(sample_episode.id) == 1


def test_create_version_placeholder_increments(
    version_service: ScriptVersionService,
    sample_episode: object,
) -> None:
    first = version_service.create_version_placeholder(
        sample_episode.id,
        llm_provider="ollama",
        model_name="test-model",
        prompt_version="v1.0.0",
    )
    second = version_service.create_version_placeholder(
        sample_episode.id,
        llm_provider="ollama",
        model_name="test-model",
        prompt_version="v1.0.0",
    )
    assert first.version == 1
    assert second.version == 2
    assert ScriptMetadata.objects.filter(script=second).exists()


def test_activate_script_marks_single_active_version(
    version_service: ScriptVersionService,
    sample_episode: object,
) -> None:
    first = Script.objects.create(
        episode=sample_episode,
        version=1,
        status=ScriptStatus.READY,
    )
    second = Script.objects.create(
        episode=sample_episode,
        version=2,
        status=ScriptStatus.READY,
    )
    ScriptMetadata.objects.create(script=first, is_active=True)
    ScriptMetadata.objects.create(script=second, is_active=False)

    version_service.activate_script(second)

    first_meta = ScriptMetadata.objects.get(script=first)
    second_meta = ScriptMetadata.objects.get(script=second)
    assert first_meta.is_active is False
    assert second_meta.is_active is True
    assert version_service.get_active_script(sample_episode.id) == second


def test_ensure_version_available_raises_on_conflict(
    version_service: ScriptVersionService,
    sample_episode: object,
) -> None:
    Script.objects.create(episode=sample_episode, version=1)
    with pytest.raises(ScriptVersionConflictError):
        version_service.ensure_version_available(sample_episode.id, 1)
