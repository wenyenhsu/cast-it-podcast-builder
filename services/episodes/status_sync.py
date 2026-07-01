"""Keep episode workflow status aligned with script and audio progress."""

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import Episode, EpisodeStatus
from apps.scripts.models import Script, ScriptStatus


def episode_needs_audio(episode: Episode) -> bool:
    """Return True when a ready script still has segments without audio."""
    script = (
        episode.scripts.filter(
            status__in=[ScriptStatus.READY, ScriptStatus.APPROVED],
        )
        .order_by("-version")
        .first()
    )
    if script is None:
        return False

    segment_count = script.segments.count()
    if segment_count == 0:
        return False

    ready_count = AudioAsset.objects.filter(
        script_segment__script=script,
        status=AudioAssetStatus.READY,
    ).count()
    return ready_count < segment_count


def episode_has_complete_audio(episode: Episode) -> bool:
    """Return True when the latest ready script has audio for every segment."""
    script = (
        episode.scripts.filter(
            status__in=[ScriptStatus.READY, ScriptStatus.APPROVED],
        )
        .order_by("-version")
        .first()
    )
    if script is None:
        return False

    segment_count = script.segments.count()
    if segment_count == 0:
        return False
    if episode_needs_audio(episode):
        return False

    ready_count = AudioAsset.objects.filter(
        script_segment__script=script,
        status=AudioAssetStatus.READY,
    ).count()
    return ready_count >= segment_count


def episode_display_status(episode: Episode) -> str:
    """Map episode workflow state to a UI status key for operations badges."""
    if episode.status == EpisodeStatus.GENERATING_SCRIPT:
        return EpisodeStatus.GENERATING_SCRIPT
    if episode.status == EpisodeStatus.GENERATING_AUDIO:
        return EpisodeStatus.GENERATING_AUDIO
    if episode_needs_audio(episode):
        return "ready_to_audio"
    if episode_has_complete_audio(episode):
        return EpisodeStatus.GENERATING_AUDIO
    return episode.status


def sync_episode_idle_status(episode: Episode) -> None:
    """Return episode to draft when it is not actively generating."""
    if episode.status in {
        EpisodeStatus.GENERATING_SCRIPT,
        EpisodeStatus.GENERATING_AUDIO,
    }:
        episode.status = EpisodeStatus.DRAFT
        episode.save(update_fields=["status", "updated_at"])
