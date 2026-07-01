"""Script validation helpers for the API layer."""

from apps.scripts.models import Script
from domain.scripts.exceptions import ScriptValidationError
from domain.scripts.schema import PodcastScriptSchema, ScriptSegmentSchema
from services.scripts.validation_service import (
    ScriptValidationResult,
    ScriptValidationService,
)


def validate_stored_script(script: Script) -> ScriptValidationResult:
    """Validate a persisted script model through the domain validation service."""
    segments = [
        ScriptSegmentSchema(
            speaker=segment.speaker,  # type: ignore[arg-type]
            voice=segment.voice,
            emotion=segment.emotion,
            text=segment.text,
            pause_before_seconds=segment.pause_before_seconds,
            pause_after_seconds=segment.pause_after_seconds,
        )
        for segment in script.segments.order_by("sequence")
    ]
    schema = PodcastScriptSchema(
        title=script.episode.title,
        summary=script.episode.summary or script.episode.description or "",
        segments=segments,
    )
    service = ScriptValidationService()
    try:
        return service.validate(schema)
    except ScriptValidationError as exc:
        return ScriptValidationResult(
            passed=False,
            errors=[str(exc)],
            warnings=[],
            estimated_duration_seconds=script.estimated_duration_seconds or 0,
            segment_count=len(segments),
        )
