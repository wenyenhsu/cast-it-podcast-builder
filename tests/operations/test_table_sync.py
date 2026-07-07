"""Tests for the Episodes operations tab."""

import pytest
from django.urls import reverse

from apps.episodes.models import Episode, EpisodeStatus
from apps.scripts.models import Script, ScriptStatus
from services.admin.scripts_dashboard import ScriptDashboardService


@pytest.mark.django_db
def test_list_episodes_returns_all_episodes() -> None:
    episode_with_script = Episode.objects.create(
        title="Has Script", status=EpisodeStatus.DRAFT
    )
    Script.objects.create(
        episode=episode_with_script,
        version=1,
        title="",
        status=ScriptStatus.READY,
    )
    Episode.objects.create(
        title="No Script Yet", status=EpisodeStatus.GENERATING_SCRIPT
    )

    rows = ScriptDashboardService().list_episodes()

    assert {row["episode_title"] for row in rows} == {"Has Script", "No Script Yet"}


@pytest.mark.django_db
def test_list_episodes_search_filters_by_title() -> None:
    Episode.objects.create(title="Tech Weekly", status=EpisodeStatus.DRAFT)
    Episode.objects.create(title="Sports Daily", status=EpisodeStatus.DRAFT)

    rows = ScriptDashboardService().list_episodes(search="tech")

    assert {row["episode_title"] for row in rows} == {"Tech Weekly"}


@pytest.mark.django_db
def test_episodes_tab_shows_episode_without_script(admin_client) -> None:
    Episode.objects.create(
        title="Pending Script", status=EpisodeStatus.GENERATING_SCRIPT
    )

    response = admin_client.get(reverse("operations:content"), {"view": "episodes"})
    content = response.content.decode()

    assert "Pending Script" in content
    assert "—" in content


@pytest.mark.django_db
def test_episodes_tab_search_box_renders(admin_client) -> None:
    response = admin_client.get(reverse("operations:content"), {"view": "episodes"})
    content = response.content.decode()

    assert 'name="q"' in content
    assert 'placeholder="Search episodes by title..."' in content
