"""Tests for admin dashboard statistics and operations views."""

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
def test_admin_index_renders_dashboard(admin_client) -> None:
    response = admin_client.get(reverse("admin:index"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Operations Overview" in content
    assert "Total Articles" in content


@pytest.mark.django_db
def test_operations_views_load(admin_client) -> None:
    views = [
        "admin:operations_providers",
        "admin:operations_health",
        "admin:operations_metrics",
        "admin:operations_logs",
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
    url = reverse("admin:operations_episode_pipeline", args=[episode.pk])
    response = admin_client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "News Collection" in content
    assert "Publishing" in content


@pytest.mark.django_db
def test_non_staff_cannot_access_admin(db) -> None:
    from django.contrib.auth.models import User
    from django.test import Client

    user = User.objects.create_user(username="regular", password="pass")
    client = Client()
    client.force_login(user)
    response = client.get(reverse("admin:index"))
    assert response.status_code == 302
