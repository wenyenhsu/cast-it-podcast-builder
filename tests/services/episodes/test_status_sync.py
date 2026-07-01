"""Tests for episode display status resolution."""

import pytest

from apps.episodes.models import Episode, EpisodeStatus
from apps.scripts.models import Script, ScriptSegment, ScriptStatus, Speaker
from services.episodes.status_sync import episode_display_status


@pytest.mark.django_db
def test_episode_display_status_generating_script() -> None:
    episode = Episode.objects.create(
        title="Script run",
        status=EpisodeStatus.GENERATING_SCRIPT,
    )
    assert episode_display_status(episode) == EpisodeStatus.GENERATING_SCRIPT


@pytest.mark.django_db
def test_episode_display_status_generating_audio() -> None:
    episode = Episode.objects.create(
        title="Audio run",
        status=EpisodeStatus.GENERATING_AUDIO,
    )
    assert episode_display_status(episode) == EpisodeStatus.GENERATING_AUDIO


@pytest.mark.django_db
def test_episode_display_status_ready_to_audio() -> None:
    episode = Episode.objects.create(title="Needs TTS", status=EpisodeStatus.DRAFT)
    script = Script.objects.create(
        episode=episode,
        version=1,
        title="",
        status=ScriptStatus.READY,
    )
    ScriptSegment.objects.create(
        script=script,
        sequence=1,
        speaker=Speaker.EXPERT,
        text="Hello world.",
    )
    assert episode_display_status(episode) == "ready_to_audio"


@pytest.mark.django_db
def test_episode_display_status_audio_generated_when_complete() -> None:
    from apps.audio.models import AudioAsset, AudioAssetStatus

    episode = Episode.objects.create(title="Done", status=EpisodeStatus.DRAFT)
    script = Script.objects.create(
        episode=episode,
        version=1,
        title="",
        status=ScriptStatus.READY,
    )
    segment = ScriptSegment.objects.create(
        script=script,
        sequence=1,
        speaker=Speaker.EXPERT,
        text="Hello world.",
    )
    AudioAsset.objects.create(
        episode=episode,
        script_segment=segment,
        provider="chatterbox",
        voice="default",
        file_path="/tmp/test.wav",
        status=AudioAssetStatus.READY,
        duration=1.0,
    )
    assert episode_display_status(episode) == EpisodeStatus.GENERATING_AUDIO


@pytest.mark.django_db
def test_episode_display_status_draft_without_script() -> None:
    episode = Episode.objects.create(title="Empty", status=EpisodeStatus.DRAFT)
    assert episode_display_status(episode) == EpisodeStatus.DRAFT
