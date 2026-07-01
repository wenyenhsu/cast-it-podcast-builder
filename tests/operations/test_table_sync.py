"""Tests for synced episode/script operations tables."""

import pytest
from django.urls import reverse

from apps.episodes.models import Episode, EpisodeStatus
from apps.scripts.models import Script, ScriptStatus
from services.admin.scripts_dashboard import ScriptDashboardService
from services.admin.stats import DashboardStatsService


@pytest.mark.django_db
def test_scripts_tab_lists_same_episodes_as_episodes_today() -> None:
    episode_with_script = Episode.objects.create(title="Has Script", status=EpisodeStatus.DRAFT)
    Script.objects.create(
        episode=episode_with_script,
        version=1,
        title="",
        status=ScriptStatus.READY,
    )
    Episode.objects.create(title="No Script Yet", status=EpisodeStatus.GENERATING_SCRIPT)

    episodes_today = DashboardStatsService().list_episodes_today()
    scripts = ScriptDashboardService().list_scripts(sync_with_episodes_today=True)

    assert len(episodes_today) == len(scripts)
    assert {row["title"] for row in episodes_today} == {
        row["episode_title"] for row in scripts
    }
    assert {row["display_status"] for row in episodes_today} == {
        row["display_status"] for row in scripts
    }


@pytest.mark.django_db
def test_scripts_tab_shows_episode_without_script(admin_client) -> None:
    Episode.objects.create(title="Pending Script", status=EpisodeStatus.GENERATING_SCRIPT)

    response = admin_client.get(reverse("operations:content"), {"view": "scripts"})
    content = response.content.decode()

    assert "Pending Script" in content
    assert "—" in content
