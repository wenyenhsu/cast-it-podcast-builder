"""Tests for script generation service."""

from unittest.mock import MagicMock

import pytest

from apps.episodes.models import EpisodeStatus
from apps.scripts.models import Script, ScriptStatus, ValidationStatus
from domain.llm.dtos import LLMResponse
from domain.scripts.exceptions import ScriptGenerationError, ScriptValidationError
from services.scripts.generation_service import ScriptGenerationService
from services.scripts.prompt_builder import ScriptPromptBuilder
from services.scripts.validation_service import (
    ScriptValidationConfig,
    ScriptValidationService,
)
from tests.services.scripts.conftest import build_valid_script_json


def test_generate_creates_script_and_segments(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )
    script = service.generate(sample_episode)

    assert script.status == ScriptStatus.READY
    assert script.validation_status == ValidationStatus.PASSED
    assert script.title == "AI Weekly Roundup"
    assert script.segments.count() == 6
    assert script.metadata.source_article_ids
    script.metadata.refresh_from_db()
    assert script.metadata.is_active is True
    assert script.metadata.token_usage["total_tokens"] == 300

    sample_episode.refresh_from_db()
    assert sample_episode.status == EpisodeStatus.GENERATING_SCRIPT
    mock_llm.chat.assert_called_once()


def test_generate_without_articles_raises(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    sample_episode.articles.clear()
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
    )
    with pytest.raises(ScriptGenerationError, match="no selected articles"):
        service.generate(sample_episode)


def test_generate_marks_script_failed_on_validation_error(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    mock_llm.chat.return_value = LLMResponse(
        content=build_valid_script_json(segment_count=2),
        model="test-model",
    )
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )
    with pytest.raises(ScriptValidationError):
        service.generate(sample_episode)

    script = Script.objects.get(episode=sample_episode)
    assert script.status == ScriptStatus.FAILED
    assert script.validation_status == ValidationStatus.FAILED


def test_generate_uses_json_mode(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )
    service.generate(sample_episode)
    request = mock_llm.chat.call_args.args[0]
    assert request.json_mode is True
