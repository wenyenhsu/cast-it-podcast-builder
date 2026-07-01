"""Tests for manual script entry."""

import pytest

from apps.episodes.models import Episode, EpisodeStatus
from apps.scripts.models import Script, ScriptMetadata, ScriptStatus, Speaker
from services.admin.manual_script import (
    ManualScriptError,
    ManualScriptService,
    parse_manual_script_lines,
)


def test_parse_manual_script_lines_accepts_colon_format() -> None:
    segments = parse_manual_script_lines(
        "intro: Welcome.\nexpert: Main point.\nbeginner: Question?"
    )
    assert len(segments) == 3
    assert segments[0].speaker == "intro"
    assert segments[1].text == "Main point."


def test_parse_manual_script_lines_accepts_bracket_format() -> None:
    segments = parse_manual_script_lines("[narration] Scene setting.")
    assert segments[0].speaker == "narration"


def test_parse_manual_script_lines_rejects_invalid_speaker() -> None:
    with pytest.raises(ManualScriptError, match="unknown speaker"):
        parse_manual_script_lines("host: Hello")


@pytest.mark.django_db
def test_create_manual_script_on_draft_episode() -> None:
    episode = Episode.objects.create(title="Draft Episode", status=EpisodeStatus.DRAFT)
    script = ManualScriptService().create(
        title="Manual Brief",
        dialogue="expert: Hello.\nbeginner: Hi there.",
        episode_id=str(episode.id),
    )

    assert script.status == ScriptStatus.READY
    assert script.llm_provider == "manual"
    assert script.segments.count() == 2
    assert script.segments.order_by("sequence").first().speaker == Speaker.EXPERT

    episode.refresh_from_db()
    assert episode.title == "Manual Brief"
    assert script.title == ""

    metadata = ScriptMetadata.objects.get(script=script)
    assert metadata.is_active is True


@pytest.mark.django_db
def test_create_manual_script_creates_draft_when_no_episode() -> None:
    script = ManualScriptService().create(
        title="Standalone Manual",
        dialogue="outro: Goodbye.",
    )
    assert Script.objects.filter(pk=script.id).exists()
    assert script.episode.title == "Standalone Manual"
    assert script.episode.status == EpisodeStatus.DRAFT
