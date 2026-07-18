"""Tests for script schema parsing and validation."""

import json

import pytest
from pydantic import ValidationError

from domain.scripts.exceptions import (
    ScriptEmptyError,
    ScriptSchemaError,
    ScriptValidationError,
)
from domain.scripts.schema import (
    ChapterCriticSchema,
    PodcastScriptSchema,
    ScriptSegmentSchema,
)
from services.scripts.validation_service import (
    ScriptValidationConfig,
    ScriptValidationService,
)
from tests.services.scripts.conftest import build_valid_script_json


@pytest.fixture
def validation_service() -> ScriptValidationService:
    return ScriptValidationService(
        config=ScriptValidationConfig(min_segments=4, max_segments=20)
    )


def test_parse_json_success(validation_service: ScriptValidationService) -> None:
    raw = build_valid_script_json(segment_count=6)
    schema = validation_service.parse_json(raw)
    assert schema.title == "AI Weekly Roundup"
    assert len(schema.segments) == 6


def test_parse_json_empty_raises(validation_service: ScriptValidationService) -> None:
    with pytest.raises(ScriptEmptyError):
        validation_service.parse_json("   ")


def test_parse_json_invalid_schema_raises(
    validation_service: ScriptValidationService,
) -> None:
    with pytest.raises(ScriptSchemaError):
        validation_service.parse_json('{"title": "Only title"}')


def test_validate_segment_count_minimum(
    validation_service: ScriptValidationService,
) -> None:
    schema = PodcastScriptSchema.model_validate_json(
        build_valid_script_json(segment_count=2)
    )
    with pytest.raises(ScriptValidationError, match="below minimum"):
        validation_service.validate(schema)


def test_validate_missing_required_speaker(
    validation_service: ScriptValidationService,
) -> None:
    payload = json.loads(build_valid_script_json(segment_count=6))
    payload["segments"] = [
        segment for segment in payload["segments"] if segment["speaker"] != "beginner"
    ]
    schema = PodcastScriptSchema.model_validate(payload)
    with pytest.raises(ScriptValidationError, match="Missing required speakers"):
        validation_service.validate(schema)


def test_validate_empty_segment_text(
    validation_service: ScriptValidationService,
) -> None:
    with pytest.raises(ValidationError):
        ScriptSegmentSchema(
            speaker="expert",
            voice="expert_voice",
            emotion="calm",
            text="   ",
        )


def test_validate_success_returns_duration(
    validation_service: ScriptValidationService,
) -> None:
    schema = validation_service.parse_json(build_valid_script_json(segment_count=6))
    result = validation_service.validate(schema)
    assert result.passed is True
    assert result.segment_count == 6
    assert result.estimated_duration_seconds > 0


def test_validate_rejects_critic_unsupported_claim() -> None:
    service = ScriptValidationService(
        config=ScriptValidationConfig(min_segments=4, max_segments=20)
    )
    schema = service.parse_json(build_valid_script_json(segment_count=6))
    critic = ChapterCriticSchema(
        passed=False,
        score=30,
        unsupported_claims=["The dialogue invented a 50% improvement."],
    )

    with pytest.raises(ScriptValidationError, match="50% improvement"):
        service.validate(schema, critics=[critic], expected_language="en")


def test_validate_rejects_language_mismatch() -> None:
    service = ScriptValidationService(
        config=ScriptValidationConfig(min_segments=4, max_segments=20)
    )
    schema = service.parse_json(build_valid_script_json(segment_count=6))
    critic = ChapterCriticSchema(
        passed=False,
        score=40,
        language_matches=False,
        language_issues=["The chapter is written in Spanish."],
    )

    with pytest.raises(ScriptValidationError, match="does not match language en"):
        service.validate(schema, critics=[critic], expected_language="en")


@pytest.mark.parametrize(
    ("field", "issue", "message"),
    [
        ("repetitions", "The chapter repeats its opening.", "repetition issues"),
        ("dialogue_issues", "The exchange is mechanical.", "dialogue issues"),
        ("coherence_issues", "The conclusion does not follow.", "coherence issues"),
        ("transition_issues", "The hand-off is missing.", "transition issues"),
    ],
)
def test_validate_warns_for_critic_editorial_issues(
    field: str,
    issue: str,
    message: str,
) -> None:
    service = ScriptValidationService(
        config=ScriptValidationConfig(min_segments=4, max_segments=20)
    )
    schema = service.parse_json(build_valid_script_json(segment_count=6))
    critic = ChapterCriticSchema(
        passed=True,
        score=90,
        **{field: [issue]},
    )

    result = service.validate(schema, critics=[critic], expected_language="en")

    assert result.passed is True
    assert any(message in warning for warning in result.warnings)
