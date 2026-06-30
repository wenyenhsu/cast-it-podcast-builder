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
def test_operations_views_load(admin_client) -> None:
    views = [
        "operations:providers",
        "operations:health",
        "operations:metrics",
        "operations:logs",
    ]
    for view_name in views:
        response = admin_client.get(reverse(view_name))
        assert response.status_code == 200, view_name


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
