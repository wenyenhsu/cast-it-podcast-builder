"""Article classification service."""

import logging
import time
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.articles.models import Article
from domain.intelligence.categories import ArticleCategory
from domain.intelligence.dtos import ClassificationDTO
from domain.llm.dtos import LLMRequest
from services.intelligence.parsers import parse_single_line
from services.llm.prompt_builder import PromptBuilder

if TYPE_CHECKING:
    from services.llm.service import LLMService

logger = logging.getLogger(__name__)


class ArticleClassificationService:
    """Classifies articles into predefined categories using the LLM service."""

    def __init__(
        self,
        llm_service: "LLMService",
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._llm = llm_service
        self._prompt_builder = prompt_builder or PromptBuilder()

    def classify(self, article: Article) -> ClassificationDTO:
        """Classify an article and persist the category."""
        if article.classified_at is not None and article.category.strip():
            logger.info(
                "Classification skipped, already generated",
                extra={
                    "event": "classification_skipped",
                    "article_id": str(article.id),
                },
            )
            return ClassificationDTO(
                article_id=article.id,
                category=article.category,
                classified_at=article.classified_at,
            )

        started = time.perf_counter()
        user_prompt = self._prompt_builder.build_user_prompt(
            "classification",
            {
                "title": article.title,
                "summary": article.summary or article.content[:500],
            },
        )
        system_prompt = self._prompt_builder.build_system_prompt(
            "system",
            {"show_name": "Cast It", "language": article.language},
        )

        response = self._llm.chat(
            LLMRequest(system_prompt=system_prompt, user_prompt=user_prompt)
        )
        category = ArticleCategory.from_label(parse_single_line(response.content)).value
        classified_at = timezone.now()

        article.category = category
        article.classified_at = classified_at
        article.save(update_fields=["category", "classified_at", "updated_at"])

        elapsed = time.perf_counter() - started
        logger.info(
            "Classification completed",
            extra={
                "event": "classification_completed",
                "article_id": str(article.id),
                "category": category,
                "elapsed_time": elapsed,
            },
        )

        return ClassificationDTO(
            article_id=article.id,
            category=category,
            classified_at=classified_at,
        )
