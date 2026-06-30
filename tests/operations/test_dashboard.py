"""Tests for the standalone operations dashboard."""

import pytest
from django.urls import reverse

from apps.articles.models import Article, ArticleStatus
from apps.episodes.models import Episode, EpisodeStatus
from apps.providers.models import NewsSource
from apps.scheduler.models import Job, JobStatus, JobType
from services.admin.stats import DashboardStatsService


@pytest.mark.django_db
def test_dashboard_stats_overview(news_source: NewsSource) -> None:
    Article.objects.create(
        title="Sample Article",
        source=news_source,
        url="https://example.com/article",
        content_hash="abc123",
        status=ArticleStatus.COLLECTED,
    )
    Job.objects.create(job_type=JobType.IMPORT_NEWS, status=JobStatus.RUNNING)
    Episode.objects.create(title="Episode 1", status=EpisodeStatus.DRAFT)

    stats = DashboardStatsService().overview()

    assert stats["total_articles"] == 1
    assert stats["running_jobs"] == 1
    assert stats["articles_imported_today"] == 1
    assert "provider_health" in stats


@pytest.mark.django_db
def test_operations_dashboard_renders(admin_client) -> None:
    response = admin_client.get(reverse("operations:dashboard"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Dashboard" in content
    assert "Total Articles" in content
    assert "Model administration" not in content


@pytest.mark.django_db
def test_providers_page_renders(admin_client) -> None:
    response = admin_client.get(reverse("operations:providers"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Providers" in content
    assert "Configuration" in content


@pytest.mark.django_db
def test_provider_tabs_render(admin_client) -> None:
    for tab, marker in (
        ("llm", "Available Models"),
        ("tts", "Active Voice"),
        ("sources", "Information Resources"),
    ):
        response = admin_client.get(reverse("operations:providers"), {"tab": tab})
        assert response.status_code == 200
        content = response.content.decode()
        if tab == "sources":
            assert "RSS Provider" in content
            assert "Manual Provider" in content
            assert "Add RSS Source" in content
        else:
            assert marker in content


@pytest.mark.django_db
def test_information_resource_subtabs_render(admin_client) -> None:
    rss = admin_client.get(
        reverse("operations:providers"),
        {"tab": "sources", "resource": "rss"},
    )
    assert rss.status_code == 200
    rss_content = rss.content.decode()
    assert "RSS Sources" in rss_content
    assert "Add RSS Source" in rss_content

    manual = admin_client.get(
        reverse("operations:providers"),
        {"tab": "sources", "resource": "manual"},
    )
    assert manual.status_code == 200
    manual_content = manual.content.decode()
    assert "Manual Provider" in manual_content
    assert "Add Article" in manual_content
    assert "Recent Manual Articles" in manual_content


@pytest.mark.django_db
def test_create_manual_article_from_providers_ui(admin_client) -> None:
    response = admin_client.post(
        reverse("operations:providers"),
        {
            "tab": "sources",
            "resource": "manual",
            "provider_action": "create_manual_article",
            "article_title": "UI Manual Article",
            "article_content": "Created from the operations dashboard.",
        },
    )
    assert response.status_code == 302
    assert "resource=manual" in response.url
    assert Article.objects.filter(title="UI Manual Article").exists()


@pytest.mark.django_db
def test_create_rss_source_from_providers_ui(admin_client) -> None:
    response = admin_client.post(
        reverse("operations:providers"),
        {
            "tab": "sources",
            "resource": "rss",
            "provider_action": "create_source",
            "name": "UI Feed",
            "rss_url": "https://example.com/feed.xml",
            "language": "en",
            "enabled": "on",
        },
    )
    assert response.status_code == 302
    assert "resource=rss" in response.url
    assert NewsSource.objects.filter(name="UI Feed").exists()


@pytest.mark.django_db
def test_article_detail_view(admin_client, news_source: NewsSource) -> None:
    article = Article.objects.create(
        title="Detail Article",
        source=news_source,
        url="https://example.com/detail",
        content_hash="detail-hash",
        summary="Short summary",
        content="Full article body text.",
        status=ArticleStatus.COLLECTED,
    )
    response = admin_client.get(
        reverse("operations:article_detail", args=[article.pk]),
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "Detail Article" in content
    assert "Full article body text." in content
    assert "Short summary" in content


@pytest.mark.django_db
def test_article_title_links_to_detail(admin_client, news_source: NewsSource) -> None:
    article = Article.objects.create(
        title="Linked RSS Article",
        source=news_source,
        url="https://example.com/linked",
        content_hash="linked-hash",
        status=ArticleStatus.COLLECTED,
    )
    response = admin_client.get(
        reverse("operations:providers"),
        {"tab": "sources", "resource": "rss"},
    )
    assert response.status_code == 200
    assert reverse("operations:article_detail", args=[article.pk]) in response.content.decode()


@pytest.mark.django_db
def test_legacy_provider_urls_redirect(admin_client) -> None:
    cases = [
        ("operations:llm", "tab=llm"),
        ("operations:tts", "tab=tts"),
    ]
    for view_name, fragment in cases:
        response = admin_client.get(reverse(view_name))
        assert response.status_code == 302, view_name
        assert "/providers/" in response.url
        assert fragment in response.url


@pytest.mark.django_db
def test_operations_monitor_loads(admin_client) -> None:
    response = admin_client.get(reverse("operations:monitor"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_monitor_tabs_render(admin_client) -> None:
    for tab in ("health", "metrics", "logs"):
        response = admin_client.get(reverse("operations:monitor"), {"tab": tab})
        assert response.status_code == 200
        content = response.content.decode()
        assert "Monitor" in content
        assert tab.title() in content


@pytest.mark.django_db
def test_legacy_monitor_urls_redirect(admin_client) -> None:
    cases = [
        ("operations:health", "tab=health"),
        ("operations:metrics", "tab=metrics"),
        ("operations:logs", "tab=logs"),
    ]
    for view_name, fragment in cases:
        response = admin_client.get(reverse(view_name))
        assert response.status_code == 302, view_name
        assert "/monitor/" in response.url
        assert fragment in response.url


@pytest.mark.django_db
def test_episode_pipeline_view(admin_client, news_source: NewsSource) -> None:
    episode = Episode.objects.create(
        title="Pipeline Episode",
        status=EpisodeStatus.DRAFT,
    )
    Article.objects.create(
        title="Linked Article",
        source=news_source,
        url="https://example.com/pipeline",
        content_hash="pipeline-hash",
        status=ArticleStatus.COLLECTED,
    )
    url = reverse("operations:episode_pipeline", args=[episode.pk])
    response = admin_client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "News Collection" in content
    assert "Publishing" in content
    assert "pipeline-panel" in content
    assert "Items:" in content


@pytest.mark.django_db
def test_non_staff_cannot_access_operations_dashboard(db) -> None:
    from django.contrib.auth.models import User
    from django.test import Client

    user = User.objects.create_user(username="regular", password="pass")
    client = Client()
    client.force_login(user)
    response = client.get(reverse("operations:dashboard"))
    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_admin_index_is_separate(admin_client) -> None:
    response = admin_client.get(reverse("admin:index"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Operations Overview" not in content


@pytest.mark.django_db
def test_dashboard_stats_list_methods(news_source: NewsSource) -> None:
    del news_source
    episode = Episode.objects.create(
        title="Waiting Episode",
        status=EpisodeStatus.GENERATING_SCRIPT,
    )
    Episode.objects.create(title="Draft Today", status=EpisodeStatus.DRAFT)
    Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.FAILED,
        error_message="LLM timeout",
        payload={"episode_id": str(episode.id)},
    )

    service = DashboardStatsService()
    failed = service.list_failed_jobs()
    waiting = service.list_episodes_waiting_for_audio()
    today = service.list_episodes_today()

    assert len(failed) == 1
    assert failed[0]["error_message"] == "LLM timeout"
    assert failed[0]["episode_id"] == str(episode.id)
    assert len(waiting) == 1
    assert waiting[0]["title"] == "Waiting Episode"
    assert len(today) >= 2


@pytest.mark.django_db
def test_dashboard_insights_redirects_to_content(admin_client) -> None:
    response = admin_client.get(
        reverse("operations:dashboard_insights"),
        {"tab": "failed-jobs"},
    )
    assert response.status_code == 302
    assert response.url.endswith("/content/?view=failed-jobs")


@pytest.mark.django_db
def test_content_pipeline_views(admin_client) -> None:
    Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.FAILED,
        error_message="boom",
    )
    Episode.objects.create(title="Today Ep", status=EpisodeStatus.DRAFT)
    Episode.objects.create(
        title="Audio Ep",
        status=EpisodeStatus.GENERATING_AUDIO,
    )

    failed = admin_client.get(reverse("operations:content"), {"view": "failed-jobs"})
    assert failed.status_code == 200
    assert "boom" in failed.content.decode()

    today = admin_client.get(reverse("operations:content"), {"view": "episodes-today"})
    assert today.status_code == 200
    assert "Today Ep" in today.content.decode()

    waiting = admin_client.get(
        reverse("operations:content"),
        {"view": "waiting-for-audio"},
    )
    assert waiting.status_code == 200
    assert "Audio Ep" in waiting.content.decode()

    fail_log = admin_client.get(reverse("operations:content"), {"view": "fail-log"})
    assert fail_log.status_code == 200
    assert "boom" in fail_log.content.decode()


@pytest.mark.django_db
def test_dashboard_stat_cards_link_to_content(admin_client) -> None:
    response = admin_client.get(reverse("operations:dashboard"))
    content = response.content.decode()
    assert "view=failed-jobs" in content
    assert "view=episodes-today" in content
    assert "view=waiting-for-audio" in content
