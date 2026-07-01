"""Best-effort article indexing for the knowledge base."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from domain.knowledge.dtos import IndexResult
from services.knowledge.indexing import IndexingService
from services.knowledge.normalizer import DocumentNormalizer
from services.knowledge.settings import KnowledgeSettings

if TYPE_CHECKING:
    from apps.articles.models import Article

logger = logging.getLogger(__name__)


def is_rag_enabled() -> bool:
    return KnowledgeSettings.from_django_settings().enabled


def index_article_best_effort(article: Article) -> IndexResult | None:
    """Index one article; log and return None when RAG is off or indexing fails."""
    if not is_rag_enabled():
        return None

    try:
        request = DocumentNormalizer().from_article(article)
        result = IndexingService().index_document(request)
        logger.info(
            "Article indexed for RAG",
            extra={
                "event": "article_indexed_for_rag",
                "article_id": str(article.id),
                "document_id": result.document_id,
                "chunks_created": result.chunks_created,
                "skipped": result.skipped,
            },
        )
        return result
    except Exception as exc:
        logger.warning(
            "Article indexing skipped",
            extra={
                "event": "article_indexing_failed",
                "article_id": str(article.id),
                "error": str(exc),
            },
        )
        return None


def index_articles_best_effort(articles: list[Article]) -> int:
    """Index multiple articles; returns count of successful index operations."""
    indexed = 0
    for article in articles:
        result = index_article_best_effort(article)
        if result is not None:
            indexed += 1
    return indexed
