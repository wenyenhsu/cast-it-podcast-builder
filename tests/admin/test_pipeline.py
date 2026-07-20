"""Tests for episode pipeline service."""

import pytest

from apps.episodes.models import Episode, EpisodeStatus
from apps.scheduler.models import Job, JobStatus, JobType
from services.admin.pipeline import EpisodePipelineService


@pytest.mark.django_db
def test_pipeline_stages_for_episode(news_source) -> None:
    from apps.articles.models import Article, ArticleStatus
    from apps.episodes.models import EpisodeArticle

    episode = Episode.objects.create(
        title="Pipeline Test",
        status=EpisodeStatus.GENERATING_SCRIPT,
    )
    article = Article.objects.create(
        title="Article",
        source=news_source,
        url="https://example.com/p",
        content_hash="pipe-hash",
        status=ArticleStatus.COLLECTED,
    )
    EpisodeArticle.objects.create(episode=episode, article=article)
    Job.objects.create(
        job_type=JobType.SUMMARIZE_ARTICLE,
        status=JobStatus.SUCCEEDED,
        payload={"episode_id": str(episode.id), "article_id": str(article.id)},
    )

    stages = EpisodePipelineService().build_pipeline(episode)
    names = [stage.name for stage in stages]

    assert names == list(EpisodePipelineService.STAGE_NAMES)
    assert stages[0].status in {"completed", "succeeded", "ready", "pending"}


@pytest.mark.django_db
def test_pipeline_duration_uses_article_timestamps(news_source) -> None:
    from datetime import timedelta

    from django.utils import timezone

    from apps.articles.models import Article, ArticleStatus
    from apps.episodes.models import EpisodeArticle

    now = timezone.now()
    episode = Episode.objects.create(
        title="Duration Pipeline",
        status=EpisodeStatus.DRAFT,
    )
    first = Article.objects.create(
        title="First",
        source=news_source,
        url="https://example.com/first-duration",
        content_hash="duration-1",
        status=ArticleStatus.SELECTED,
        summary="Ready summary",
        category="AI",
        importance_score=90,
        classified_at=now - timedelta(minutes=30),
    )
    second = Article.objects.create(
        title="Second",
        source=news_source,
        url="https://example.com/second-duration",
        content_hash="duration-2",
        status=ArticleStatus.SELECTED,
        summary="Ready summary",
        category="AI",
        importance_score=80,
        classified_at=now - timedelta(minutes=20),
    )
    Article.objects.filter(pk=first.pk).update(created_at=now - timedelta(hours=1))
    Article.objects.filter(pk=second.pk).update(created_at=now - timedelta(minutes=50))
    first.refresh_from_db()
    second.refresh_from_db()
    EpisodeArticle.objects.create(episode=episode, article=first)
    EpisodeArticle.objects.create(episode=episode, article=second)

    stages = {
        stage.name: stage for stage in EpisodePipelineService().build_pipeline(episode)
    }

    assert stages["News Collection"].display_status == "SUCCESS"
    assert stages["News Collection"].duration_label == "—"
    assert stages["Summary"].display_status == "SUCCESS"
    assert stages["Classification"].display_status == "SUCCESS"
    assert stages["Classification"].duration_seconds
    assert stages["Classification"].duration_seconds > 0
    assert stages["Ranking"].display_status == "SUCCESS"
    assert stages["Script"].duration_label == "—"


@pytest.mark.django_db
def test_pipeline_as_dicts(news_source) -> None:
    episode = Episode.objects.create(
        title="Dict Pipeline",
        status=EpisodeStatus.DRAFT,
    )
    panel = EpisodePipelineService().build_panel(episode)
    stage_dicts = panel["stages"]
    assert len(stage_dicts) == 5
    assert all(stage["name"] != "Publishing" for stage in stage_dicts)
    assert all(stage["name"] != "Audio" for stage in stage_dicts)
    assert "name" in stage_dicts[0]
    assert "display_status" in stage_dicts[0]
    assert "description" in stage_dicts[0]
    assert panel["overview"]["progress_percent"] >= 0
    assert len(panel["overview"]["metrics"]) == 4
