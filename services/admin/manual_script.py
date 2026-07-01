"""Manual script entry for operations (bypass LLM, feed TTS directly)."""

import re
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.episodes.models import Episode, EpisodeStatus
from services.episodes.title import apply_episode_name, normalize_episode_name
from apps.scripts.models import (
    Script,
    ScriptMetadata,
    ScriptSegment,
    ScriptStatus,
    Speaker,
    ValidationStatus,
)
from domain.scripts.schema import ScriptSegmentSchema
from services.admin.content_library import ContentLibraryService
from services.scripts.duration_estimator import (
    estimate_segment_duration_seconds,
    estimate_total_duration_seconds,
)
from services.scripts.version_service import ScriptVersionService

_SPEAKER_VALUES = {choice.value for choice in Speaker}
_BRACKET_PATTERN = re.compile(
    r"^\s*\[(?P<speaker>[^\]]+)\]\s*(?P<text>.+?)\s*$",
    re.IGNORECASE,
)
_COLON_PATTERN = re.compile(
    r"^\s*(?P<speaker>[^:]+?)\s*:\s*(?P<text>.+?)\s*$",
    re.IGNORECASE,
)


class ManualScriptError(Exception):
    """Raised when manual script input fails validation."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def parse_manual_script_lines(text: str) -> list[ScriptSegmentSchema]:
    """Parse dialogue lines in ``speaker: text`` or ``[speaker] text`` format."""
    if not text.strip():
        raise ManualScriptError("Dialogue is required. Add at least one segment.")

    segments: list[ScriptSegmentSchema] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = _BRACKET_PATTERN.match(line) or _COLON_PATTERN.match(line)
        if not match:
            raise ManualScriptError(
                f"Line {line_number} is invalid. Use "
                f'"expert: Your line here" or "[beginner] Your line here".'
            )

        speaker = match.group("speaker").strip().lower()
        if speaker not in _SPEAKER_VALUES:
            allowed = ", ".join(sorted(_SPEAKER_VALUES))
            raise ManualScriptError(
                f"Line {line_number} has unknown speaker '{speaker}'. "
                f"Use one of: {allowed}."
            )

        segment_text = match.group("text").strip()
        if not segment_text:
            raise ManualScriptError(f"Line {line_number} has empty dialogue text.")

        segments.append(
            ScriptSegmentSchema(
                speaker=speaker,  # type: ignore[arg-type]
                text=segment_text,
            )
        )

    if not segments:
        raise ManualScriptError("Add at least one dialogue segment.")

    return segments


class ManualScriptService:
    """Creates ready-to-use scripts from pasted dialogue."""

    def __init__(
        self,
        *,
        content_library: ContentLibraryService | None = None,
        version_service: ScriptVersionService | None = None,
    ) -> None:
        self._content_library = content_library or ContentLibraryService()
        self._version_service = version_service or ScriptVersionService()

    def resolve_episode(self, episode_id: str | None = None) -> Episode:
        if episode_id:
            try:
                return Episode.objects.get(pk=episode_id)
            except Episode.DoesNotExist as exc:
                raise ManualScriptError("Episode not found.") from exc
        return self._content_library.ensure_draft_episode()

    @transaction.atomic
    def create(
        self,
        *,
        title: str,
        dialogue: str,
        episode_id: str | None = None,
    ) -> Script:
        cleaned_title = normalize_episode_name(title)
        if not cleaned_title:
            raise ManualScriptError("Episode name is required.")

        parsed_segments = parse_manual_script_lines(dialogue)
        episode = self.resolve_episode(episode_id)
        apply_episode_name(episode, cleaned_title)
        episode.status = EpisodeStatus.DRAFT
        episode.save(update_fields=["status", "updated_at"])
        version = self._version_service.get_next_version(episode.id)

        script = Script.objects.create(
            episode=episode,
            version=version,
            title="",
            llm_provider="manual",
            model_name="",
            prompt_version="manual",
            status=ScriptStatus.READY,
            validation_status=ValidationStatus.PASSED,
            estimated_duration_seconds=estimate_total_duration_seconds(parsed_segments),
            generated_at=timezone.now(),
        )

        ScriptSegment.objects.bulk_create(
            [
                ScriptSegment(
                    script=script,
                    sequence=index,
                    speaker=segment.speaker,
                    voice=segment.voice,
                    emotion=segment.emotion,
                    text=segment.text,
                    pause_before_seconds=segment.pause_before_seconds,
                    pause_after_seconds=segment.pause_after_seconds,
                    estimated_duration_seconds=estimate_segment_duration_seconds(
                        segment
                    ),
                )
                for index, segment in enumerate(parsed_segments, start=1)
            ]
        )

        metadata, _ = ScriptMetadata.objects.get_or_create(
            script=script,
            defaults={
                "is_active": False,
                "source_article_ids": [],
                "selected_topics": [],
            },
        )
        metadata.generation_notes = "Manual script entry (no LLM)."
        metadata.validation_results = {
            "passed": True,
            "errors": [],
            "warnings": [],
            "segment_count": len(parsed_segments),
            "estimated_duration_seconds": script.estimated_duration_seconds,
        }
        metadata.save(
            update_fields=["generation_notes", "validation_results", "updated_at"]
        )

        self._version_service.activate_script(script)

        return script

    def form_defaults(self, request_post: dict[str, Any] | None = None) -> dict[str, str]:
        if request_post and request_post.get("script_action") == "create_manual_script":
            return {
                "title": str(request_post.get("script_title", "")),
                "dialogue": str(request_post.get("script_dialogue", "")),
            }
        return {"title": "", "dialogue": ""}
