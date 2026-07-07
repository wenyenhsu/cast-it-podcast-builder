"""Tests for the operations content dashboard."""

import pytest
from django.urls import reverse

from apps.articles.models import Article, ArticleStatus
from apps.episodes.models import Episode, EpisodeArticle, EpisodeStatus
from apps.scripts.models import Script, ScriptStatus
from apps.providers.models import NewsSource, ProviderType
from apps.scheduler.models import Job, JobStatus, JobType
from services.admin.content_library import ContentLibraryError, ContentLibraryService


@pytest.mark.django_db
def test_content_page_renders_unified_table(admin_client, news_source: NewsSource) -> None:
    Article.objects.create(
        title="RSS Story",
        source=news_source,
        url="https://example.com/rss-story",
        content_hash="rss-story-hash",
        status=ArticleStatus.COLLECTED,
    )
    response = admin_client.get(reverse("operations:content"))
    content = response.content.decode()
    assert "Articles" in content
    assert "Script Generation" in content
    assert "RSS Story" in content
    assert "generateScriptModal" in content
    assert 'name="episode_title"' in content


@pytest.mark.django_db
def test_content_filter_shows_subset_in_same_table(
    admin_client,
    news_source: NewsSource,
) -> None:
    manual_source = NewsSource.objects.create(
        name="Manual Entry",
        provider_type=ProviderType.MANUAL,
        enabled=True,
    )
    Article.objects.create(
        title="RSS Only",
        source=news_source,
        url="https://example.com/rss-only",
        content_hash="rss-only-hash",
        status=ArticleStatus.COLLECTED,
    )
    Article.objects.create(
        title="Manual Only",
        source=manual_source,
        url="https://example.com/manual-only",
        content_hash="manual-only-hash",
        status=ArticleStatus.COLLECTED,
    )

    all_response = admin_client.get(reverse("operations:content"))
    all_content = all_response.content.decode()
    assert "RSS Only" in all_content
    assert "Manual Only" in all_content

    rss = admin_client.get(reverse("operations:content"), {"type": "rss"})
    rss_content = rss.content.decode()
    assert "RSS Only" in rss_content
    assert "Manual Only" not in rss_content


@pytest.mark.django_db
def test_save_script_sources_updates_articles_and_draft_episode(
    admin_client,
    news_source: NewsSource,
) -> None:
    article = Article.objects.create(
        title="Selectable Story",
        source=news_source,
        url="https://example.com/selectable",
        content_hash="selectable-hash",
        status=ArticleStatus.COLLECTED,
    )
    episode = Episode.objects.create(title="Draft", status=EpisodeStatus.DRAFT)

    response = admin_client.post(
        reverse("operations:content"),
        {
            "content_action": "save_script_sources",
            "type": "all",
            "article_scope_ids": [str(article.id)],
            "script_source_ids": [str(article.id)],
        },
    )
    assert response.status_code == 302
    article.refresh_from_db()
    assert article.selected_for_script is True
    assert EpisodeArticle.objects.filter(episode=episode, article=article).exists()


@pytest.mark.django_db
def test_filtered_save_does_not_clear_other_type_selection(
    admin_client,
    news_source: NewsSource,
) -> None:
    manual_source = NewsSource.objects.create(
        name="Manual Entry",
        provider_type=ProviderType.MANUAL,
        enabled=True,
    )
    rss_article = Article.objects.create(
        title="RSS Item",
        source=news_source,
        url="https://example.com/rss-item",
        content_hash="rss-item-hash",
        status=ArticleStatus.COLLECTED,
        selected_for_script=True,
    )
    manual_article = Article.objects.create(
        title="Manual Item",
        source=manual_source,
        url="https://example.com/manual-item",
        content_hash="manual-item-hash",
        status=ArticleStatus.COLLECTED,
        selected_for_script=True,
    )

    response = admin_client.post(
        reverse("operations:content"),
        {
            "content_action": "save_script_sources",
            "type": "rss",
            "article_scope_ids": [str(rss_article.id)],
            "script_source_ids": [],
        },
    )
    assert response.status_code == 302
    rss_article.refresh_from_db()
    manual_article.refresh_from_db()
    assert rss_article.selected_for_script is False
    assert manual_article.selected_for_script is True


@pytest.mark.django_db
def test_generate_script_from_content_ui_redirects_with_job(
    admin_client,
    news_source: NewsSource,
    mock_job_dispatch,
) -> None:
    del mock_job_dispatch
    Article.objects.create(
        title="Script Source",
        source=news_source,
        url="https://example.com/script-source",
        content_hash="script-source-hash",
        status=ArticleStatus.COLLECTED,
        selected_for_script=True,
    )

    response = admin_client.post(
        reverse("operations:content"),
        {
            "content_action": "generate_script",
            "episode_title": "Morning Tech Brief",
            "type": "all",
        },
    )
    assert response.status_code == 302
    assert "job=" in response.url
    episode = Episode.objects.get(status=EpisodeStatus.DRAFT)
    assert episode.title == "Morning Tech Brief"


@pytest.mark.django_db
def test_job_status_api(admin_client) -> None:
    job = Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.RUNNING,
        progress=42,
    )
    response = admin_client.get(reverse("operations:job_status_api", args=[job.pk]))
    assert response.status_code == 200
    data = response.json()
    assert data["progress"] == 42
    assert data["label"] == "Script Generation"
    assert data["is_terminal"] is False


@pytest.mark.django_db
def test_generate_script_from_content_ui(
    admin_client,
    news_source: NewsSource,
    mock_job_dispatch,
) -> None:
    del mock_job_dispatch
    Article.objects.create(
        title="Script Source",
        source=news_source,
        url="https://example.com/script-source",
        content_hash="script-source-hash",
        status=ArticleStatus.COLLECTED,
        selected_for_script=True,
    )

    response = admin_client.post(
        reverse("operations:content"),
        {
            "content_action": "generate_script",
            "episode_title": "Weekly Roundup",
            "type": "all",
        },
    )
    assert response.status_code == 302
    assert Episode.objects.filter(status=EpisodeStatus.DRAFT, title="Weekly Roundup").exists()


@pytest.mark.django_db
def test_generate_script_requires_episode_title(
    admin_client,
    news_source: NewsSource,
) -> None:
    Article.objects.create(
        title="Script Source",
        source=news_source,
        url="https://example.com/script-source",
        content_hash="script-source-hash",
        status=ArticleStatus.COLLECTED,
        selected_for_script=True,
    )

    response = admin_client.post(
        reverse("operations:content"),
        {
            "content_action": "generate_script",
            "episode_title": "   ",
            "type": "all",
        },
    )
    assert response.status_code == 200
    assert "Episode name is required" in response.content.decode()


@pytest.mark.django_db
def test_queue_script_generation_rejects_duplicate_active_job(
    news_source: NewsSource,
) -> None:
    episode = Episode.objects.create(title="Draft", status=EpisodeStatus.DRAFT)
    Article.objects.create(
        title="Source",
        source=news_source,
        url="https://example.com/source",
        content_hash="source-hash",
        selected_for_script=True,
    )
    Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.RUNNING,
        payload={"episode_id": str(episode.id)},
    )
    service = ContentLibraryService()
    with pytest.raises(ContentLibraryError, match="already running"):
        service.queue_script_generation(episode_title="Draft")


@pytest.mark.django_db
def test_abort_script_generation_cancels_active_job(
    news_source: NewsSource,
) -> None:
    episode = Episode.objects.create(title="Draft", status=EpisodeStatus.DRAFT)
    Article.objects.create(
        title="Source",
        source=news_source,
        url="https://example.com/source",
        content_hash="source-hash",
        selected_for_script=True,
    )
    job = Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.QUEUED,
        payload={"episode_id": str(episode.id)},
    )
    service = ContentLibraryService()
    aborted_id = service.abort_script_generation()
    assert aborted_id == str(job.id)
    job.refresh_from_db()
    assert job.status == JobStatus.CANCELLED


@pytest.mark.django_db
def test_abort_script_from_content_ui(admin_client, news_source: NewsSource) -> None:
    episode = Episode.objects.create(title="Draft", status=EpisodeStatus.DRAFT)
    Article.objects.create(
        title="Source",
        source=news_source,
        url="https://example.com/source",
        content_hash="source-hash",
        selected_for_script=True,
    )
    Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.QUEUED,
        payload={"episode_id": str(episode.id)},
    )

    response = admin_client.post(
        reverse("operations:content"),
        {
            "content_action": "abort_script",
            "type": "all",
        },
    )
    assert response.status_code == 302
    assert "aborted_job=" in response.url

    page = admin_client.get(reverse("operations:content"))
    content = page.content.decode()
    assert "Generate Script" in content
    assert "btn-outline-danger" not in content


@pytest.mark.django_db
def test_content_shows_abort_while_script_queued(
    admin_client,
    news_source: NewsSource,
) -> None:
    episode = Episode.objects.create(title="Draft", status=EpisodeStatus.DRAFT)
    Article.objects.create(
        title="Source",
        source=news_source,
        url="https://example.com/source",
        content_hash="source-hash",
        selected_for_script=True,
    )
    Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.QUEUED,
        payload={"episode_id": str(episode.id)},
    )

    response = admin_client.get(reverse("operations:content"))
    content = response.content.decode()
    assert "Generating..." in content
    assert "Abort" in content
    assert 'id="generate-script-btn"' not in content


@pytest.mark.django_db
def test_delete_episode_from_content_ui(admin_client) -> None:
    episode = Episode.objects.create(title="Delete Me", status=EpisodeStatus.DRAFT)
    script = Script.objects.create(
        episode=episode,
        version=1,
        title="",
        status=ScriptStatus.READY,
    )

    response = admin_client.post(
        reverse("operations:content"),
        {
            "content_action": "delete_episode",
            "episode_id": str(episode.id),
            "content_view": "episodes",
            "type": "all",
        },
    )
    assert response.status_code == 302
    assert "view=episodes" in response.url
    assert not Episode.objects.filter(pk=episode.id).exists()
    assert not Script.objects.filter(pk=script.id).exists()


@pytest.mark.django_db
def test_episodes_view_has_delete_not_admin(admin_client) -> None:
    Episode.objects.create(title="Any Ep", status=EpisodeStatus.DRAFT)
    response = admin_client.get(
        reverse("operations:content"),
        {"view": "episodes"},
    )
    content = response.content.decode()
    assert "Delete" in content
    assert "admin:episodes_episode_change" not in content
    assert "admin:episodes_episode_changelist" not in content


@pytest.mark.django_db
def test_queue_script_generation_requires_selection(news_source: NewsSource) -> None:
    del news_source
    service = ContentLibraryService()
    with pytest.raises(ContentLibraryError):
        service.queue_script_generation(episode_title="")


@pytest.mark.django_db
def test_queue_script_generation_creates_new_episode(
    news_source: NewsSource,
    mock_job_dispatch,
) -> None:
    del mock_job_dispatch
    existing = Episode.objects.create(title="Old Draft", status=EpisodeStatus.DRAFT)
    Article.objects.create(
        title="Source",
        source=news_source,
        url="https://example.com/source",
        content_hash="source-hash",
        status=ArticleStatus.COLLECTED,
        selected_for_script=True,
    )

    service = ContentLibraryService()
    episode_id, _ = service.queue_script_generation(episode_title="Brand New Show")

    assert episode_id != str(existing.id)
    assert Episode.objects.filter(pk=existing.id).exists()
    new_episode = Episode.objects.get(pk=episode_id)
    assert new_episode.title == "Brand New Show"
    assert Episode.objects.count() == 2


@pytest.mark.django_db
def test_delete_failed_job_from_content_ui(admin_client) -> None:
    job = Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.FAILED,
        error_message="boom",
    )
    response = admin_client.post(
        reverse("operations:content"),
        {
            "content_action": "delete_failed_job",
            "job_id": str(job.id),
            "content_view": "failed-jobs",
            "type": "all",
        },
    )
    assert response.status_code == 302
    assert "view=failed-jobs" in response.url
    assert not Job.objects.filter(pk=job.id).exists()


@pytest.mark.django_db
def test_content_scripts_tab_link(admin_client) -> None:
    response = admin_client.get(reverse("operations:content"))
    content = response.content.decode()
    assert "view=scripts" in content
    assert "Scripts" in content


@pytest.mark.django_db
def test_content_library_service_counts() -> None:
    totals = ContentLibraryService().article_totals()
    assert "total_articles" in totals
    assert "selected_for_script" in totals
