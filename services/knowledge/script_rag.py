"""RAG context assembly for podcast script generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from apps.knowledge.models import SourceType
from domain.knowledge.dtos import RetrievalFilter
from domain.knowledge.exceptions import ContextBuildError, RetrievalError
from services.knowledge.article_indexing import index_articles_best_effort
from services.knowledge.context_builder import ContextBuilder
from services.knowledge.settings import KnowledgeSettings

if TYPE_CHECKING:
    from apps.articles.models import Article
    from apps.episodes.models import Episode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScriptRagResult:
    """Outcome of RAG enrichment for script generation."""

    context_text: str
    chunks_used: int
    articles_indexed: int
    enabled: bool


class ScriptRagService:
    """Retrieve supplemental article context for script prompts."""

    def __init__(
        self,
        settings: KnowledgeSettings | None = None,
        context_builder: ContextBuilder | None = None,
    ) -> None:
        self._settings = settings or KnowledgeSettings.from_django_settings()
        self._context_builder = context_builder

    def enrich(
        self,
        episode: Episode,
        articles: list[Article],
    ) -> ScriptRagResult:
        """Ensure articles are indexed and return assembled retrieval context."""
        if not self._settings.enabled:
            return ScriptRagResult(
                context_text="",
                chunks_used=0,
                articles_indexed=0,
                enabled=False,
            )

        articles_indexed = index_articles_best_effort(articles)
        query = _build_retrieval_query(episode, articles)
        if not query:
            return ScriptRagResult(
                context_text="",
                chunks_used=0,
                articles_indexed=articles_indexed,
                enabled=True,
            )

        try:
            builder = self._context_builder or ContextBuilder(self._settings)
            assembled = builder.build(
                query,
                filters=RetrievalFilter(
                    language=episode.language,
                    source_type=SourceType.ARTICLE,
                ),
            )
        except (RetrievalError, ContextBuildError) as exc:
            logger.warning(
                "Script RAG context skipped",
                extra={
                    "event": "script_rag_context_failed",
                    "episode_id": str(episode.id),
                    "error": str(exc),
                },
            )
            return ScriptRagResult(
                context_text="",
                chunks_used=0,
                articles_indexed=articles_indexed,
                enabled=True,
            )

        logger.info(
            "Script RAG context assembled",
            extra={
                "event": "script_rag_context_assembled",
                "episode_id": str(episode.id),
                "articles_indexed": articles_indexed,
                "chunks_retrieved": assembled.chunks_retrieved,
                "chunks_used": assembled.chunks_used,
                "total_tokens": assembled.total_tokens,
            },
        )
        return ScriptRagResult(
            context_text=assembled.context_text,
            chunks_used=assembled.chunks_used,
            articles_indexed=articles_indexed,
            enabled=True,
        )

    def enrich_article(
        self,
        episode: Episode,
        article: Article,
    ) -> ScriptRagResult:
        """Retrieve context constrained to one article's indexed chunks."""
        if not self._settings.enabled:
            return ScriptRagResult("", 0, 0, False)

        articles_indexed = index_articles_best_effort([article])
        query = "\n".join(
            part for part in (article.title.strip(), article.summary.strip()) if part
        )
        if not query:
            return ScriptRagResult("", 0, articles_indexed, True)

        try:
            builder = self._context_builder or ContextBuilder(self._settings)
            assembled = builder.build(
                query,
                filters=RetrievalFilter(
                    language=article.language or episode.language,
                    source_type=SourceType.ARTICLE,
                    source_id=str(article.id),
                ),
            )
        except (RetrievalError, ContextBuildError) as exc:
            logger.warning(
                "Article-specific script RAG context skipped",
                extra={
                    "event": "script_article_rag_context_failed",
                    "episode_id": str(episode.id),
                    "article_id": str(article.id),
                    "error": str(exc),
                },
            )
            return ScriptRagResult("", 0, articles_indexed, True)

        return ScriptRagResult(
            context_text=assembled.context_text,
            chunks_used=assembled.chunks_used,
            articles_indexed=articles_indexed,
            enabled=True,
        )


def _build_retrieval_query(episode: Episode, articles: list[Article]) -> str:
    titles = "; ".join(
        article.title.strip() for article in articles[:8] if article.title
    )
    categories = ", ".join(
        sorted({article.category.strip() for article in articles if article.category})
    )
    parts = [
        episode.title.strip(),
        episode.summary.strip(),
        titles,
        categories,
    ]
    return "\n".join(part for part in parts if part)
