"""Tests for script schema parsing and validation."""

import json

import pytest
from pydantic import ValidationError

from domain.scripts.exceptions import (
    ScriptEmptyError,
    ScriptSchemaError,
    ScriptValidationError,
)
from domain.scripts.schema import PodcastScriptSchema, ScriptSegmentSchema
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
