"""Script validation service."""

import logging
import re
from dataclasses import dataclass, field

from domain.scripts.constants import (
    MAX_ESTIMATED_DURATION_SECONDS,
    MAX_SEGMENTS,
    MIN_SEGMENTS,
    WORDS_PER_MINUTE,
)
from domain.scripts.exceptions import (
    ScriptEmptyError,
    ScriptSchemaError,
    ScriptValidationError,
)
from domain.scripts.schema import (
    REQUIRED_SPEAKERS,
    ChapterCriticSchema,
    PodcastScriptSchema,
    ScriptSegmentSchema,
)
from services.scripts.duration_estimator import estimate_total_duration_seconds

logger = logging.getLogger(__name__)

DIALOGUE_SPEAKERS = frozenset({"expert", "beginner"})


@dataclass(frozen=True)
class ScriptValidationConfig:
    """Configurable validation limits for generated scripts."""

    min_segments: int = MIN_SEGMENTS
    max_segments: int = MAX_SEGMENTS
    max_duration_seconds: int = MAX_ESTIMATED_DURATION_SECONDS
    words_per_minute: int = WORDS_PER_MINUTE
    require_alternating_dialogue: bool = True


@dataclass
class ScriptValidationResult:
    """Outcome of script validation."""

    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    estimated_duration_seconds: int = 0
    segment_count: int = 0


class ScriptValidationService:
    """Validates structured podcast script output before persistence."""

    def __init__(self, config: ScriptValidationConfig | None = None) -> None:
        self._config = config or ScriptValidationConfig()

    def parse_json(self, raw_content: str) -> PodcastScriptSchema:
        """Parse and validate raw LLM JSON output."""
        if not raw_content.strip():
            raise ScriptEmptyError("LLM returned empty script content.")

        try:
            schema = PodcastScriptSchema.model_validate_json(raw_content)
        except Exception as exc:
            raise ScriptSchemaError(f"Invalid script JSON schema: {exc}") from exc

        logger.info(
            "Script schema validation succeeded",
            extra={
                "event": "script_schema_validated",
                "segment_count": len(schema.segments),
            },
        )
        return schema

    def validate(
        self,
        script: PodcastScriptSchema,
        *,
        critics: list[ChapterCriticSchema] | None = None,
        expected_language: str = "",
    ) -> ScriptValidationResult:
        """Run full business validation on a parsed script."""
        errors: list[str] = []
        warnings: list[str] = []

        segment_count = len(script.segments)
        if segment_count < self._config.min_segments:
            errors.append(
                f"Segment count {segment_count} is below minimum "
                f"{self._config.min_segments}."
            )
        if segment_count > self._config.max_segments:
            errors.append(
                f"Segment count {segment_count} exceeds maximum "
                f"{self._config.max_segments}."
            )

        speakers_present = {segment.speaker for segment in script.segments}
        missing_speakers = REQUIRED_SPEAKERS - speakers_present
        if missing_speakers:
            errors.append(
                f"Missing required speakers: {', '.join(sorted(missing_speakers))}."
            )

        self._validate_empty_text(script.segments, errors)
        self._validate_speaker_sequence(script.segments, errors, warnings)
        self._validate_content_quality(
            script.segments,
            critics or [],
            expected_language,
            errors,
            warnings,
        )

        estimated_duration = estimate_total_duration_seconds(
            script.segments,
            words_per_minute=self._config.words_per_minute,
        )
        if estimated_duration > self._config.max_duration_seconds:
            errors.append(
                f"Estimated duration {estimated_duration}s exceeds maximum "
                f"{self._config.max_duration_seconds}s."
            )

        passed = not errors
        result = ScriptValidationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            estimated_duration_seconds=estimated_duration,
            segment_count=segment_count,
        )

        if passed:
            logger.info(
                "Script validation passed",
                extra={
                    "event": "script_validation_passed",
                    "segment_count": segment_count,
                    "estimated_duration_seconds": estimated_duration,
                },
            )
        else:
            logger.warning(
                "Script validation failed",
                extra={
                    "event": "script_validation_failed",
                    "errors": errors,
                    "segment_count": segment_count,
                },
            )
            raise ScriptValidationError("; ".join(errors))

        return result

    def _validate_content_quality(
        self,
        segments: list[ScriptSegmentSchema],
        critics: list[ChapterCriticSchema],
        expected_language: str,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """Reject critic-detected grounding failures and obvious repetition."""
        for index, critic in enumerate(critics, start=1):
            if critic.unsupported_claims:
                errors.append(
                    f"Chapter {index} has unsupported claims: "
                    + "; ".join(critic.unsupported_claims)
                )
            if critic.missing_facts:
                warnings.append(
                    f"Chapter {index} is missing facts: "
                    + "; ".join(critic.missing_facts)
                )
            if not critic.language_matches:
                errors.append(
                    f"Chapter {index} does not match language {expected_language}: "
                    + "; ".join(critic.language_issues or ["language mismatch"])
                )
            elif critic.language_issues:
                warnings.append(
                    f"Chapter {index} has language style issues: "
                    + "; ".join(critic.language_issues)
                )
            for label, issues in (
                ("repetition", critic.repetitions),
                ("dialogue", critic.dialogue_issues),
                ("coherence", critic.coherence_issues),
                ("transition", critic.transition_issues),
            ):
                if issues:
                    warnings.append(
                        f"Chapter {index} has {label} issues: " + "; ".join(issues)
                    )
            if not critic.passed:
                if critic.unsupported_claims or not critic.language_matches:
                    errors.append(f"Chapter {index} did not pass content review.")
                else:
                    warnings.append(
                        f"Chapter {index} reached the rewrite limit with "
                        "editorial issues."
                    )

        seen: set[str] = set()
        for index, segment in enumerate(segments, start=1):
            normalized = re.sub(r"\W+", " ", segment.text.lower()).strip()
            if len(normalized) < 30:
                continue
            if normalized in seen:
                errors.append(f"Segment {index} exactly repeats an earlier segment.")
            seen.add(normalized)

        if not critics:
            warnings.append("No structured chapter critic results were provided.")

    def _validate_empty_text(
        self,
        segments: list[ScriptSegmentSchema],
        errors: list[str],
    ) -> None:
        for index, segment in enumerate(segments, start=1):
            if not segment.text.strip():
                errors.append(f"Segment {index} has empty text.")

    def _validate_speaker_sequence(
        self,
        segments: list[ScriptSegmentSchema],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        dialogue_segments = [
            segment for segment in segments if segment.speaker in DIALOGUE_SPEAKERS
        ]
        if len(dialogue_segments) < 2:
            errors.append("Dialogue must include at least two expert/beginner turns.")
            return

        if not self._config.require_alternating_dialogue:
            return

        previous_speaker: str | None = None
        consecutive_count = 0
        for segment in dialogue_segments:
            if segment.speaker == previous_speaker:
                consecutive_count += 1
                if consecutive_count >= 3:
                    warnings.append(
                        f"Speaker '{segment.speaker}' has three or more "
                        "consecutive dialogue turns."
                    )
            else:
                consecutive_count = 1
                previous_speaker = segment.speaker

        expert_count = sum(1 for s in dialogue_segments if s.speaker == "expert")
        beginner_count = sum(1 for s in dialogue_segments if s.speaker == "beginner")
        ratio = min(expert_count, beginner_count) / max(expert_count, beginner_count)
        if ratio < 0.3:
            warnings.append(
                "Dialogue balance is uneven between expert and beginner speakers."
            )
