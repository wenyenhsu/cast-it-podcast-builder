"""News source management for the operations providers dashboard."""

import uuid
from typing import Any
from urllib.parse import urlparse

from django.db.models import Count
from django.utils import timezone

from apps.articles.models import Article, ArticleStatus
from apps.providers.models import NewsSource, ProviderType
from services.admin.actions import AdminOperationsService
from services.news.content_hash import ContentHashService

MANUAL_SOURCE_NAME = "Manual Entry"


class NewsSourceFormError(Exception):
    """Raised when news source form validation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NewsSourceDashboardService:
    """CRUD and import helpers for information resources (news sources)."""

    def list_sources(
        self,
        *,
        provider_type: str | None = None,
    ) -> list[dict[str, Any]]:
        sources = NewsSource.objects.annotate(article_count=Count("articles")).order_by(
            "name"
        )
        if provider_type:
            sources = sources.filter(provider_type=provider_type)
        return [
            {
                "id": str(source.id),
                "name": source.name,
                "provider_type": source.provider_type,
                "rss_url": source.rss_url,
                "homepage": source.homepage,
                "language": source.language,
                "enabled": source.enabled,
                "max_articles_per_import": source.max_articles_per_import,
                "article_count": source.article_count,
                "created_at": source.created_at,
            }
            for source in sources
        ]

    def recent_articles(
        self,
        *,
        provider_type: str | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        articles = Article.objects.select_related("source").order_by("-created_at")
        if provider_type:
            articles = articles.filter(source__provider_type=provider_type)
        articles = articles[:limit]
        return [
            {
                "id": str(article.id),
                "title": article.title,
                "source_name": article.source.name if article.source else "—",
                "created_at": article.created_at,
            }
            for article in articles
        ]

    def article_totals(self) -> dict[str, int]:
        return {
            "total_articles": Article.objects.count(),
            "rss_articles": Article.objects.filter(
                source__provider_type=ProviderType.RSS
            ).count(),
            "manual_articles": Article.objects.filter(
                source__provider_type=ProviderType.MANUAL
            ).count(),
            "rss_sources": NewsSource.objects.filter(
                provider_type=ProviderType.RSS
            ).count(),
            "enabled_rss_sources": NewsSource.objects.filter(
                provider_type=ProviderType.RSS,
                enabled=True,
            ).count(),
        }

    def manual_provider_overview(self) -> dict[str, Any]:
        source = self.get_or_create_manual_source()
        article_count = Article.objects.filter(source=source).count()
        return {
            "id": str(source.id),
            "name": source.name,
            "provider_type": source.provider_type,
            "language": source.language,
            "enabled": source.enabled,
            "article_count": article_count,
        }

    def get_edit_form(self, source_id: str) -> dict[str, Any] | None:
        try:
            source = NewsSource.objects.get(pk=source_id)
        except NewsSource.DoesNotExist:
            return None
        if source.provider_type != ProviderType.RSS:
            return None
        return {
            "id": str(source.id),
            "name": source.name,
            "rss_url": source.rss_url,
            "language": source.language,
            "enabled": source.enabled,
            "max_articles_per_import": source.max_articles_per_import,
        }

    def create_rss_source(
        self,
        *,
        name: str,
        rss_url: str,
        language: str = "en",
        enabled: bool = True,
        max_articles_per_import: int = 3,
    ) -> NewsSource:
        cleaned = self._validate_rss_payload(
            name=name,
            rss_url=rss_url,
            language=language,
            max_articles_per_import=max_articles_per_import,
        )
        return NewsSource.objects.create(
            name=cleaned["name"],
            provider_type=ProviderType.RSS,
            rss_url=cleaned["rss_url"],
            language=cleaned["language"],
            enabled=enabled,
            max_articles_per_import=cleaned["max_articles_per_import"],
        )

    def update_rss_source(
        self,
        source_id: str,
        *,
        name: str,
        rss_url: str,
        language: str,
        enabled: bool,
        max_articles_per_import: int,
    ) -> NewsSource:
        source = NewsSource.objects.get(pk=source_id)
        cleaned = self._validate_rss_payload(
            name=name,
            rss_url=rss_url,
            language=language,
            max_articles_per_import=max_articles_per_import,
        )
        source.name = cleaned["name"]
        source.rss_url = cleaned["rss_url"]
        source.language = cleaned["language"]
        source.enabled = enabled
        source.max_articles_per_import = cleaned["max_articles_per_import"]
        source.provider_type = ProviderType.RSS
        source.save(
            update_fields=[
                "name",
                "rss_url",
                "language",
                "enabled",
                "max_articles_per_import",
                "provider_type",
                "updated_at",
            ]
        )
        return source

    def delete_source(self, source_id: str) -> None:
        NewsSource.objects.filter(pk=source_id).delete()

    def import_source(self, source_id: str, *, user_id: int | None) -> str:
        source = NewsSource.objects.get(pk=source_id)
        if source.provider_type != ProviderType.RSS:
            raise NewsSourceFormError("Only RSS sources support import.")
        job_ids = AdminOperationsService().import_sources(
            NewsSource.objects.filter(pk=source.pk),
            user_id=user_id,
        )
        return job_ids[0] if job_ids else ""

    def get_or_create_manual_source(self) -> NewsSource:
        source, _ = NewsSource.objects.get_or_create(
            name=MANUAL_SOURCE_NAME,
            provider_type=ProviderType.MANUAL,
            defaults={"enabled": True, "language": "en"},
        )
        return source

    def create_manual_article(
        self,
        *,
        source_id: str,
        title: str,
        content: str,
        summary: str = "",
        author: str = "",
        url: str = "",
    ) -> Article:
        cleaned_title = title.strip()
        cleaned_content = content.strip()
        cleaned_summary = summary.strip()
        cleaned_author = author.strip()
        cleaned_url = url.strip()

        if not cleaned_title:
            raise NewsSourceFormError("Title is required.")
        if not cleaned_content and not cleaned_summary:
            raise NewsSourceFormError("Content or summary is required.")

        if source_id:
            try:
                source = NewsSource.objects.get(pk=source_id)
            except NewsSource.DoesNotExist as exc:
                raise NewsSourceFormError("Source not found.") from exc
        else:
            source = self.get_or_create_manual_source()

        if cleaned_url:
            parsed = urlparse(cleaned_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise NewsSourceFormError("URL must be a valid http(s) address.")
        else:
            cleaned_url = f"https://manual.cast-it.local/{uuid.uuid4()}"

        body = cleaned_content or cleaned_summary
        content_hash = ContentHashService().generate_hash(
            body,
            fallback_title=cleaned_title,
        )
        if Article.objects.filter(content_hash=content_hash).exists():
            raise NewsSourceFormError("An article with the same content already exists.")

        return Article.objects.create(
            source=source,
            title=cleaned_title,
            author=cleaned_author,
            url=cleaned_url,
            published_at=timezone.now(),
            language=source.language,
            summary=cleaned_summary,
            content=cleaned_content,
            content_hash=content_hash,
            status=ArticleStatus.COLLECTED,
        )

    def toggle_source_enabled(self, source_id: str, *, enabled: bool) -> NewsSource:
        source = NewsSource.objects.get(pk=source_id)
        if source.provider_type == ProviderType.RSS:
            edit = self.get_edit_form(source_id)
            if edit is None:
                raise NewsSourceFormError("Source not found.")
            return self.update_rss_source(
                source_id,
                name=edit["name"],
                rss_url=edit["rss_url"],
                language=edit["language"],
                enabled=enabled,
                max_articles_per_import=edit["max_articles_per_import"],
            )
        source.enabled = enabled
        source.save(update_fields=["enabled", "updated_at"])
        return source

    def _validate_rss_payload(
        self,
        *,
        name: str,
        rss_url: str,
        language: str,
        max_articles_per_import: int = 3,
    ) -> dict[str, str | int]:
        cleaned_name = name.strip()
        cleaned_url = rss_url.strip()
        cleaned_language = language.strip() or "en"
        if not cleaned_name:
            raise NewsSourceFormError("Name is required.")
        if not cleaned_url:
            raise NewsSourceFormError("RSS URL is required.")
        parsed = urlparse(cleaned_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise NewsSourceFormError("RSS URL must be a valid http(s) address.")
        if len(cleaned_language) > 10:
            raise NewsSourceFormError("Language code is too long.")
        if max_articles_per_import < 0 or max_articles_per_import > 100:
            raise NewsSourceFormError("Articles per import must be between 0 and 100.")
        return {
            "name": cleaned_name,
            "rss_url": cleaned_url,
            "language": cleaned_language,
            "max_articles_per_import": max_articles_per_import,
        }
