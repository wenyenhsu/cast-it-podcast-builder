"""Script library views for the operations dashboard."""

from typing import Any

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import Episode
from apps.scripts.models import Script, ScriptSegment, ScriptStatus
from services.admin.stats import DashboardStatsService
from services.episodes.status_sync import episode_display_status


class ScriptDashboardService:
    """Read-only script listing and detail helpers."""

    def list_scripts(self, *, episode_id: str = "", sync_with_episodes_today: bool = False) -> list[dict[str, Any]]:
        """List script rows; optionally align with Episodes Today."""
        if sync_with_episodes_today and not episode_id:
            return self._list_episode_rows(
                DashboardStatsService._episodes_today_queryset().order_by("-updated_at")
            )
        if episode_id:
            return self._list_episode_rows(
                Episode.objects.filter(pk=episode_id).order_by("-updated_at")
            )

        scripts = Script.objects.select_related("episode").prefetch_related("segments")
        scripts = scripts.order_by("-generated_at", "-created_at")
        return [
            self._serialize_script_row(script, script.episode)
            for script in scripts
        ]

    def list_episodes(self, *, search: str = "") -> list[dict[str, Any]]:
        """List all episodes as script rows, optionally filtered by title search."""
        episodes = Episode.objects.all()
        term = (search or "").strip()
        if term:
            episodes = episodes.filter(title__icontains=term)
        return self._list_episode_rows(episodes.order_by("-updated_at"))

    def _list_episode_rows(self, episodes) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for episode in episodes.prefetch_related("scripts__segments"):
            latest = (
                episode.scripts.exclude(status=ScriptStatus.FAILED)
                .order_by("-version")
                .first()
                or episode.scripts.order_by("-version").first()
            )
            rows.append(self._serialize_script_row(latest, episode))
        return rows

    @staticmethod
    def _serialize_script_row(script: Script | None, episode: Episode) -> dict[str, Any]:
        tts_script = (
            episode.scripts.filter(
                status__in=[ScriptStatus.READY, ScriptStatus.APPROVED],
            )
            .order_by("-version")
            .first()
        )
        return {
            "id": str(script.id) if script else "",
            "episode_id": str(episode.id),
            "episode_title": episode.title,
            "version": script.version if script else None,
            "title": episode.title,
            "status": script.status if script else "",
            "display_status": episode_display_status(episode),
            "validation_status": script.validation_status if script else "",
            "llm_provider": script.llm_provider if script else "",
            "model_name": script.model_name if script else "",
            "segment_count": script.segments.count() if script else 0,
            "estimated_duration_seconds": script.estimated_duration_seconds if script else None,
            "generated_at": script.generated_at if script else None,
            "created_at": script.created_at if script else episode.created_at,
            "updated_at": episode.updated_at,
            "tts_script_id": str(tts_script.id) if tts_script else "",
            "can_generate_tts": bool(tts_script),
        }

    def delete_script(self, script_id: str) -> dict[str, str]:
        """Delete the parent episode (and all scripts/audio) for a script row."""
        try:
            script = Script.objects.select_related("episode").get(pk=script_id)
        except Script.DoesNotExist as exc:
            raise ValueError("Script not found.") from exc
        return self.delete_episode(str(script.episode_id))

    def delete_episode(self, episode_id: str) -> dict[str, str]:
        """Delete an episode and all related scripts/audio."""
        try:
            episode = Episode.objects.get(pk=episode_id)
        except Episode.DoesNotExist as exc:
            raise ValueError("Episode not found.") from exc

        label = episode.title
        episode.delete()
        return {
            "episode_title": label,
            "episode_id": episode_id,
            "version": "",
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
