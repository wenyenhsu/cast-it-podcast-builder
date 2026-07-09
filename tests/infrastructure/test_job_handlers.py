"""Tests for scheduled-job target resolution in job handlers."""

from types import SimpleNamespace

import pytest

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import Episode, EpisodeStatus
from apps.scripts.models import Script, ScriptStatus
from domain.jobs.exceptions import JobPermanentError
from infrastructure.jobs.handlers import (
    _resolve_episode_for_script,
    _resolve_script_for_audio,
)


def scheduled_job() -> SimpleNamespace:
    return SimpleNamespace(payload={"scheduled": True})


@pytest.mark.django_db
def test_scheduled_script_run_picks_newest_unscripted_draft() -> None:
    scripted = Episode.objects.create(title="old", status=EpisodeStatus.DRAFT)
    Script.objects.create(episode=scripted, version=1, status=ScriptStatus.READY)
    unscripted = Episode.objects.create(title="new", status=EpisodeStatus.DRAFT)

    assert _resolve_episode_for_script(scheduled_job()).id == unscripted.id


@pytest.mark.django_db
def test_scheduled_script_run_without_candidates_raises() -> None:
    episode = Episode.objects.create(title="done", status=EpisodeStatus.COMPLETED)
    Script.objects.create(episode=episode, version=1, status=ScriptStatus.READY)

    with pytest.raises(JobPermanentError):
        _resolve_episode_for_script(scheduled_job())


@pytest.mark.django_db
def test_scheduled_audio_run_picks_script_without_final_audio() -> None:
    published = Episode.objects.create(title="has audio", status=EpisodeStatus.DRAFT)
    Script.objects.create(episode=published, version=1, status=ScriptStatus.READY)
    AudioAsset.objects.create(
        episode=published,
        provider="ffmpeg",
        voice="",
        file_path="audio/final.mp3",
        is_final_episode_audio=True,
        status=AudioAssetStatus.READY,
    )
    pending = Episode.objects.create(title="needs audio", status=EpisodeStatus.DRAFT)
    target = Script.objects.create(
        episode=pending, version=1, status=ScriptStatus.READY
    )

    assert _resolve_script_for_audio(scheduled_job()).id == target.id


@pytest.mark.django_db
def test_scheduled_audio_run_without_candidates_raises() -> None:
    with pytest.raises(JobPermanentError):
        _resolve_script_for_audio(scheduled_job())
