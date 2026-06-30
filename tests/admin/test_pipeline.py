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
def test_pipeline_as_dicts(news_source) -> None:
    episode = Episode.objects.create(
        title="Dict Pipeline",
        status=EpisodeStatus.DRAFT,
    )
    panel = EpisodePipelineService().build_panel(episode)
    stage_dicts = panel["stages"]
    assert len(stage_dicts) == 7
    assert "name" in stage_dicts[0]
    assert "display_status" in stage_dicts[0]
    assert "description" in stage_dicts[0]
    assert panel["overview"]["progress_percent"] >= 0
    assert len(panel["overview"]["metrics"]) == 5
