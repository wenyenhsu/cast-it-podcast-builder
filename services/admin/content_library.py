"""Article library management for the operations content dashboard."""

from typing import Any

from apps.articles.models import Article
from apps.episodes.models import Episode, EpisodeArticle, EpisodeStatus
from apps.providers.models import ProviderType


class ContentLibraryService:
    """Lists articles and manages script source selection."""

    def article_totals(self) -> dict[str, int]:
        return {
            "total_articles": Article.objects.count(),
            "rss_articles": Article.objects.filter(
                source__provider_type=ProviderType.RSS
            ).count(),
            "manual_articles": Article.objects.filter(
                source__provider_type=ProviderType.MANUAL
            ).count(),
            "selected_for_script": Article.objects.filter(
                selected_for_script=True
            ).count(),
        }

    def list_articles(
        self,
        *,
        provider_type: str | None = None,
    ) -> list[dict[str, Any]]:
        articles = Article.objects.select_related("source").order_by("-created_at")
        if provider_type:
            articles = articles.filter(source__provider_type=provider_type)
        return [
            {
                "id": str(article.id),
                "title": article.title,
                "source_name": article.source.name if article.source else "—",
                "provider_type": (
                    article.source.provider_type if article.source else ""
                ),
                "created_at": article.created_at,
                "status": article.status,
                "selected_for_script": article.selected_for_script,
            }
            for article in articles
        ]

    def update_script_selection(
        self,
        *,
        selected_ids: set[str],
        scope_ids: set[str],
    ) -> int:
        articles = Article.objects.filter(id__in=scope_ids)
        updated = 0
        for article in articles:
            should_select = str(article.id) in selected_ids
            if article.selected_for_script != should_select:
                article.selected_for_script = should_select
                article.save(update_fields=["selected_for_script", "updated_at"])
                updated += 1
        return updated

    def sync_selected_articles_to_draft_episode(self) -> str | None:
        episode = (
            Episode.objects.filter(
                status__in=[EpisodeStatus.DRAFT, EpisodeStatus.COLLECTING]
            )
            .order_by("-created_at")
            .first()
        )
        if episode is None:
            return None

        selected_articles = list(
            Article.objects.filter(selected_for_script=True).order_by("-created_at")
        )
        selected_ids = {article.id for article in selected_articles}
        EpisodeArticle.objects.filter(episode=episode).exclude(
            article_id__in=selected_ids
        ).delete()
        for article in selected_articles:
            EpisodeArticle.objects.get_or_create(episode=episode, article=article)
        return str(episode.id)
