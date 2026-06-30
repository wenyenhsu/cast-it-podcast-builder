"""Tests for the operations content dashboard."""

import pytest
from django.urls import reverse

from apps.articles.models import Article, ArticleStatus
from apps.episodes.models import Episode, EpisodeArticle, EpisodeStatus
from apps.providers.models import NewsSource, ProviderType
from services.admin.content_library import ContentLibraryService


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
    assert response.status_code == 200
    content = response.content.decode()
    assert "Articles" in content
    assert "RSS Story" in content
    assert "Type" in content


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
def test_content_library_service_counts() -> None:
    totals = ContentLibraryService().article_totals()
    assert "total_articles" in totals
    assert "selected_for_script" in totals
