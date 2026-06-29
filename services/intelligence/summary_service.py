"""Article summarization service."""

import logging
import time
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.articles.models import Article, ArticleStatus
from domain.intelligence.dtos import SummaryDTO
from domain.llm.dtos import LLMRequest
from services.intelligence.parsers import parse_single_line
from services.llm.prompt_builder import PromptBuilder

if TYPE_CHECKING:
    from services.llm.service import LLMService

logger = logging.getLogger(__name__)


class ArticleSummaryService:
    """Generates and persists article summaries using the LLM service."""

    def __init__(
        self,
        llm_service: "LLMService",
        prompt_builder: PromptBuilder | None = None,
        max_words: int = 120,
    ) -> None:
        self._llm = llm_service
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._max_words = max_words

    def summarize(self, article: Article) -> SummaryDTO | None:
        """Summarize an article unless it was already summarized."""
        if article.summary_generated_at is not None and article.summary.strip():
            logger.info(
                "Summary skipped, already generated",
                extra={
                    "event": "summary_skipped",
                    "article_id": str(article.id),
                },
            )
            return SummaryDTO(
                article_id=article.id,
                summary=article.summary,
                generated_at=article.summary_generated_at,
            )

        started = time.perf_counter()
        user_prompt = self._prompt_builder.build_user_prompt(
            "summary",
            {
                "title": article.title,
                "author": article.author or "Unknown",
                "published_at": str(article.published_at or ""),
                "content": article.content or article.summary,
                "max_words": str(self._max_words),
            },
        )
        system_prompt = self._prompt_builder.build_system_prompt(
            "system",
            {"show_name": "Cast It", "language": article.language},
        )

        response = self._llm.chat(
            LLMRequest(system_prompt=system_prompt, user_prompt=user_prompt)
        )
        summary = parse_single_line(response.content)
        generated_at = timezone.now()

        article.summary = summary
        article.summary_generated_at = generated_at
        if article.status == ArticleStatus.COLLECTED:
            article.status = ArticleStatus.PROCESSED
        article.save(
            update_fields=["summary", "summary_generated_at", "status", "updated_at"]
        )

        elapsed = time.perf_counter() - started
        logger.info(
            "Summary completed",
            extra={
                "event": "summary_completed",
                "article_id": str(article.id),
                "elapsed_time": elapsed,
            },
        )

        return SummaryDTO(
            article_id=article.id,
            summary=summary,
            generated_at=generated_at,
        )
