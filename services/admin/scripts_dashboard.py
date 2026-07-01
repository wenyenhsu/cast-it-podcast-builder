"""Script library views for the operations dashboard."""

from typing import Any

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.scripts.models import Script, ScriptSegment
from services.episodes.status_sync import episode_display_status


class ScriptDashboardService:
    """Read-only script listing and detail helpers."""

    def list_scripts(self, *, episode_id: str = "") -> list[dict[str, Any]]:
        scripts = Script.objects.select_related("episode").prefetch_related("segments")
        if episode_id:
            scripts = scripts.filter(episode_id=episode_id)
        scripts = scripts.order_by("-generated_at", "-created_at")
        return [
            {
                "id": str(script.id),
                "episode_id": str(script.episode_id),
                "episode_title": script.episode.title,
                "version": script.version,
                "title": script.episode.title,
                "status": script.status,
                "display_status": episode_display_status(script.episode),
                "validation_status": script.validation_status,
                "llm_provider": script.llm_provider,
                "model_name": script.model_name,
                "segment_count": script.segments.count(),
                "estimated_duration_seconds": script.estimated_duration_seconds,
                "generated_at": script.generated_at,
                "created_at": script.created_at,
            }
            for script in scripts
        ]

    def delete_script(self, script_id: str) -> dict[str, str]:
        """Delete a script and return display metadata for messaging."""
        try:
            script = Script.objects.select_related("episode").get(pk=script_id)
        except Script.DoesNotExist as exc:
            raise ValueError("Script not found.") from exc

        label = script.episode.title
        version = script.version
        episode_id = str(script.episode_id)
        script.delete()
        return {
            "episode_title": label,
            "version": str(version),
            "episode_id": episode_id,
        }

    def get_script_detail(self, script_id: str) -> dict[str, Any] | None:
        try:
            script = (
                Script.objects.select_related("episode")
                .prefetch_related("segments", "metadata")
                .get(pk=script_id)
            )
        except Script.DoesNotExist:
            return None

        metadata = getattr(script, "metadata", None)
        segments = []
        ready_audio_count = 0
        for segment in script.segments.order_by("sequence"):
            asset = (
                AudioAsset.objects.filter(
                    script_segment=segment,
                    status=AudioAssetStatus.READY,
                )
                .order_by("-generated_at")
                .first()
            )
            segment_data: dict[str, Any] = {
                "id": str(segment.id),
                "sequence": segment.sequence,
                "speaker": segment.speaker,
                "voice": segment.voice,
                "emotion": segment.emotion,
                "text": segment.text,
                "estimated_duration_seconds": segment.estimated_duration_seconds,
                "audio_asset_id": "",
                "audio_duration_seconds": None,
            }
            if asset is not None:
                segment_data["audio_asset_id"] = str(asset.id)
                segment_data["audio_duration_seconds"] = asset.duration
                ready_audio_count += 1
            segments.append(segment_data)
        return {
            "id": str(script.id),
            "episode_id": str(script.episode_id),
            "episode_title": script.episode.title,
            "version": script.version,
            "title": script.episode.title,
            "status": script.status,
            "validation_status": script.validation_status,
            "llm_provider": script.llm_provider,
            "model_name": script.model_name,
            "prompt_version": script.prompt_version,
            "estimated_duration_seconds": script.estimated_duration_seconds,
            "generated_at": script.generated_at,
            "created_at": script.created_at,
            "source_article_count": len(metadata.source_article_ids)
            if metadata
            else 0,
            "generation_notes": metadata.generation_notes if metadata else "",
            "segments": segments,
            "ready_audio_count": ready_audio_count,
            "has_generated_audio": ready_audio_count > 0,
        }
