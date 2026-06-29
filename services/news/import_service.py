"""News import orchestration service."""

import logging
from dataclasses import dataclass, field

from django.db import transaction
from django.utils.text import slugify

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils.text import slugify

from apps.articles.models import Article, ArticleStatus, ArticleTag, Tag
from apps.providers.models import NewsSource, ProviderType
from domain.dtos.article import ArticleDTO
from services.news.content_hash import ContentHashService
from services.news.duplicate_detector import DuplicateDetector
from services.news.validation import ArticleValidator

if TYPE_CHECKING:
    from infrastructure.news.providers.base import BaseNewsProvider

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Summary of a news import operation."""

    imported: int = 0
    skipped_duplicates: int = 0
    skipped_invalid: int = 0
    created_sources: int = 0
    errors: list[str] = field(default_factory=list)


class NewsImportService:
    """Orchestrates collecting, validating, and persisting news articles."""

    def __init__(
        self,
        hash_service: ContentHashService | None = None,
        validator: ArticleValidator | None = None,
        duplicate_detector: DuplicateDetector | None = None,
    ) -> None:
        self._hash_service = hash_service or ContentHashService()
        self._validator = validator or ArticleValidator()
        self._duplicate_detector = duplicate_detector or DuplicateDetector()

    def import_from_provider(self, provider: "BaseNewsProvider") -> ImportResult:
        """Collect articles from a provider and persist valid, unique entries."""
        result = ImportResult()

        logger.info(
            "Import started",
            extra={
                "event": "import_started",
                "provider": provider.__class__.__name__,
                "source": provider.source_name,
            },
        )

        try:
            articles = provider.collect()
        except Exception as exc:
            message = f"Provider collection failed: {exc}"
            logger.exception(
                "Import failed during collection",
                extra={
                    "event": "import_error",
                    "provider": provider.__class__.__name__,
                    "source": provider.source_name,
                },
            )
            result.errors.append(message)
            return result

        for dto in articles:
            self._process_article(dto, provider, result)

        logger.info(
            "Import finished",
            extra={
                "event": "import_finished",
                "provider": provider.__class__.__name__,
                "source": provider.source_name,
                "imported": result.imported,
                "skipped_duplicates": result.skipped_duplicates,
                "skipped_invalid": result.skipped_invalid,
            },
        )
        return result

    def _process_article(
        self,
        dto: ArticleDTO,
        provider: "BaseNewsProvider",
        result: ImportResult,
    ) -> None:
        if not provider.validate(dto):
            result.skipped_invalid += 1
            return

        content_hash = self._hash_service.generate_hash(
            dto.content,
            fallback_title=dto.title,
        )

        if self._duplicate_detector.is_duplicate(
            content_hash=content_hash,
            url=dto.url,
        ):
            result.skipped_duplicates += 1
            return

        try:
            with transaction.atomic():
                source, created = self._get_or_create_source(dto, provider)
                if created:
                    result.created_sources += 1

                article = Article.objects.create(
                    source=source,
                    title=dto.title.strip(),
                    author=dto.author.strip(),
                    url=dto.url.strip(),
                    published_at=dto.published_at,
                    language=dto.language or source.language,
                    category=dto.category.strip(),
                    summary=dto.summary.strip(),
                    content=dto.content.strip(),
                    content_hash=content_hash,
                    status=ArticleStatus.COLLECTED,
                )
                self._save_tags(article, dto.tags)
        except Exception as exc:
            message = f"Failed to save article '{dto.title}': {exc}"
            logger.exception(
                "Article persistence failed",
                extra={
                    "event": "import_error",
                    "url": dto.url,
                    "source": dto.source,
                },
            )
            result.errors.append(message)
            return

        result.imported += 1

    def _get_or_create_source(
        self,
        dto: ArticleDTO,
        provider: "BaseNewsProvider",
    ) -> tuple[NewsSource, bool]:
        source_name = dto.source.strip() or provider.source_name
        provider_type = self._resolve_provider_type(provider)

        source, created = NewsSource.objects.get_or_create(
            name=source_name,
            defaults={
                "provider_type": provider_type,
                "homepage": provider.config.homepage,
                "rss_url": provider.config.rss_url,
                "language": dto.language or provider.config.language,
                "enabled": True,
            },
        )
        return source, created

    @staticmethod
    def _resolve_provider_type(provider: "BaseNewsProvider") -> str:
        configured = provider.config.provider_type
        valid_types = {choice.value for choice in ProviderType}
        if configured in valid_types:
            return configured
        return ProviderType.RSS

    @staticmethod
    def _save_tags(article: Article, tags: list[str]) -> None:
        for tag_name in tags:
            normalized = tag_name.strip()
            if not normalized:
                continue

            slug = slugify(normalized) or normalized.lower().replace(" ", "-")
            tag, _ = Tag.objects.get_or_create(
                slug=slug,
                defaults={"name": normalized},
            )
            ArticleTag.objects.get_or_create(article=article, tag=tag)
