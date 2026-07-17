"""Article importance scoring service."""

import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.articles.models import Article
from domain.intelligence.dtos import ScoreDTO
from domain.llm.dtos import LLMRequest
from services.intelligence.parsers import parse_integer_response
from services.llm.prompt_builder import PromptBuilder

if TYPE_CHECKING:
    from services.llm.service import LLMService

logger = logging.getLogger(__name__)


class ArticleScoreService:
    """Calculates and persists article importance scores."""

    CATEGORY_BOOST = {
        "AI": 1.0,
        "Security": 0.95,
        "Cloud": 0.9,
        "Programming": 0.85,
        "DevOps": 0.85,
        "Data": 0.85,
        "Startup": 0.8,
        "Open Source": 0.8,
        "Other": 0.7,
    }

    def __init__(
        self,
        llm_service: "LLMService",
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._llm = llm_service
        self._prompt_builder = prompt_builder or PromptBuilder()

    def score(self, article: Article) -> ScoreDTO:
        """Generate and store an importance score for an article."""
        started = time.perf_counter()
        # llm_score = self._fetch_llm_score(article)
        freshness_score = self._freshness_score(article.published_at)
        # source_score = self._source_score(article)
        category_score = self._category_score(article.category)
        keyword_score = self._keyword_score(article)

        weighted = (
            freshness_score * 50
            + category_score * 25
            + keyword_score * 25
        )
        final_score = int(max(0, min(100, round(weighted))))
        scored_at = timezone.now()

        article.importance_score = final_score
        article.save(update_fields=["importance_score", "updated_at"])

        elapsed = time.perf_counter() - started
        logger.info(
            "Article scoring completed",
            extra={
                "event": "scoring_completed",
                "article_id": str(article.id),
                "score": final_score,
                "elapsed_time": elapsed,
            },
        )

        return ScoreDTO(
            article_id=article.id,
            score=final_score,
            freshness_score=freshness_score * 100,
            # source_score=source_score * 100,
            category_score=category_score * 100,
            keyword_score=keyword_score * 100,
            # llm_score=float(llm_score),
            scored_at=scored_at,
        )

    def _fetch_llm_score(self, article: Article) -> float:
        keywords = ", ".join(article.tags.values_list("name", flat=True))
        user_prompt = self._prompt_builder.build_user_prompt(
            "importance",
            {
                "title": article.title,
                "category": article.category or "Other",
                "keywords": keywords,
                "summary": article.summary or article.content[:500],
                "published_at": str(article.published_at or ""),
            },
        )
        system_prompt = self._prompt_builder.build_system_prompt(
            "system",
            {"show_name": "Cast It", "language": article.language},
        )
        response = self._llm.chat(
            LLMRequest(system_prompt=system_prompt, user_prompt=user_prompt)
        )
        return float(parse_integer_response(response.content, minimum=0, maximum=100))

    @staticmethod
    def _freshness_score(published_at: datetime | None) -> float:
        if published_at is None:
            return 0.4
        age_hours = (timezone.now() - published_at).total_seconds() / 3600
        if age_hours <= 24:
            return 1.0
        if age_hours <= 72:
            return 0.8
        if age_hours <= 168:
            return 0.6
        return 0.4

    @staticmethod
    def _source_score(article: Article) -> float:
        return 1.0 if article.source.enabled else 0.5

    def _category_score(self, category: str) -> float:
        return self.CATEGORY_BOOST.get(category, 0.7)

    @staticmethod
    def _keyword_score(article: Article) -> float:
        keyword_count = article.tags.count()
        if keyword_count >= 10:
            return 1.0
        if keyword_count >= 5:
            return 0.8
        if keyword_count >= 1:
            return 0.6
        return 0.3
