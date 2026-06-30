"""Tests for admin bulk actions."""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.test import RequestFactory

from apps.articles.admin import ArticleAdmin
from apps.articles.models import Article, ArticleStatus
from apps.episodes.models import Episode, EpisodeStatus
from apps.providers.admin import NewsSourceAdmin
from apps.providers.models import NewsSource
from apps.scheduler.models import Job, JobStatus, JobType


def _attach_request(request: HttpRequest, user: User) -> HttpRequest:
    middleware = SessionMiddleware(lambda _request: None)
    middleware.process_request(request)
    request.session.save()
    request.user = user
    request._messages = FallbackStorage(request)
    return request


@pytest.mark.django_db
def test_news_source_import_action(
    staff_user: User,
    news_source: NewsSource,
    mock_job_dispatch,
) -> None:
    admin = NewsSourceAdmin(NewsSource, AdminSite())
    request = _attach_request(RequestFactory().post("/"), staff_user)
    queryset = NewsSource.objects.filter(pk=news_source.pk)

    admin.import_selected(request, queryset)

    job = Job.objects.get()
    assert job.job_type == JobType.IMPORT_NEWS
    assert job.payload["source_id"] == str(news_source.id)


@pytest.mark.django_db
def test_news_source_enable_disable(staff_user: User, news_source: NewsSource) -> None:
    admin = NewsSourceAdmin(NewsSource, AdminSite())
    request = _attach_request(RequestFactory().post("/"), staff_user)
    queryset = NewsSource.objects.filter(pk=news_source.pk)

    admin.disable_sources(request, queryset)
    news_source.refresh_from_db()
    assert news_source.enabled is False

    admin.enable_sources(request, queryset)
    news_source.refresh_from_db()
    assert news_source.enabled is True


@pytest.mark.django_db
def test_article_resummarize_action(
    staff_user: User,
    news_source: NewsSource,
    mock_job_dispatch,
) -> None:
    article = Article.objects.create(
        title="Article",
        source=news_source,
        url="https://example.com/a",
        content_hash="hash1",
        status=ArticleStatus.COLLECTED,
    )
    admin = ArticleAdmin(Article, AdminSite())
    request = _attach_request(RequestFactory().post("/"), staff_user)

    admin.resummarize_selected(request, Article.objects.filter(pk=article.pk))

    job = Job.objects.get()
    assert job.job_type == JobType.SUMMARIZE_ARTICLE
    assert job.payload["article_id"] == str(article.id)


@pytest.mark.django_db
def test_add_articles_to_draft_episode(
    staff_user: User,
    news_source: NewsSource,
) -> None:
    episode = Episode.objects.create(title="Draft", status=EpisodeStatus.DRAFT)
    article = Article.objects.create(
        title="Article",
        source=news_source,
        url="https://example.com/b",
        content_hash="hash2",
        status=ArticleStatus.COLLECTED,
    )
    admin = ArticleAdmin(Article, AdminSite())
    request = _attach_request(RequestFactory().post("/"), staff_user)

    admin.add_to_episode(request, Article.objects.filter(pk=article.pk))

    assert episode.articles.filter(pk=article.pk).exists()


@pytest.mark.django_db
def test_retry_failed_jobs_action(staff_user: User, mock_job_dispatch) -> None:
    from apps.scheduler.admin import JobAdmin

    failed = Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.FAILED,
        payload={"episode_id": "ep-1"},
    )
    admin = JobAdmin(Job, AdminSite())
    request = _attach_request(RequestFactory().post("/"), staff_user)

    admin.retry_failed_jobs(request, Job.objects.filter(pk=failed.pk))

    assert Job.objects.filter(status=JobStatus.QUEUED).exists()
