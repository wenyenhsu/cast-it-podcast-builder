"""Tests for episode title helpers."""

import pytest

from apps.episodes.models import Episode, EpisodeStatus
from apps.scripts.models import Script, ScriptStatus
from services.episodes.title import (
    consolidate_legacy_script_titles,
    is_placeholder_episode_title,
    normalize_episode_name,
)


def test_normalize_episode_name_strips_prefix() -> None:
    assert normalize_episode_name("Episode: AI Weekly") == "AI Weekly"


def test_is_placeholder_episode_title() -> None:
    assert is_placeholder_episode_title("Draft 2026-06-30") is True
    assert is_placeholder_episode_title("AI Weekly") is False


@pytest.mark.django_db
def test_consolidate_legacy_script_titles() -> None:
    episode = Episode.objects.create(
        title="Draft 2026-06-30",
        status=EpisodeStatus.DRAFT,
    )
    Script.objects.create(
        episode=episode,
        version=1,
        title="Episode: AI Weekly — Manual test",
        status=ScriptStatus.READY,
    )

    updated = consolidate_legacy_script_titles()

    episode.refresh_from_db()
    script = Script.objects.get(episode=episode)
    assert updated >= 1
    assert episode.title == "AI Weekly — Manual test"
    assert script.title == ""
