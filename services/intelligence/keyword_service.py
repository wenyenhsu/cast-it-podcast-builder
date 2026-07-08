"""Keyword extraction service."""

import logging
import time
from typing import TYPE_CHECKING

from django.utils import timezone
from django.utils.text import slugify

from apps.articles.models import Article, ArticleTag, Tag
from domain.intelligence.constants import ALLOWED_TAGS, MAX_KEYWORDS, MIN_KEYWORDS
from domain.intelligence.dtos import KeywordDTO
from domain.llm.dtos import LLMRequest
from services.intelligence.parsers import parse_keywords
from services.llm.prompt_builder import PromptBuilder

if TYPE_CHECKING:
    from services.llm.service import LLMService

logger = logging.getLogger(__name__)


class KeywordExtractionService:
    """Extracts keywords from articles and stores them as tags."""

    def __init__(
        self,
        llm_service: "LLMService",
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._llm = llm_service
        self._prompt_builder = prompt_builder or PromptBuilder()

    def extract(self, article: Article) -> KeywordDTO:
        """Extract keywords unless they were already generated."""
        if article.keywords_generated_at is not None:
            existing = list(article.tags.values_list("name", flat=True))
            logger.info(
                "Keyword extraction skipped, already generated",
                extra={
                    "event": "keywords_skipped",
                    "article_id": str(article.id),
                },
            )
            return KeywordDTO(
                article_id=article.id,
                keywords=existing,
                extracted_at=article.keywords_generated_at,
            )

        started = time.perf_counter()
        user_prompt = self._prompt_builder.build_user_prompt(
            "keywords",
            {
                "title": article.title,
                "category": article.category or "Other",
                "summary": article.summary or article.content[:500],
                "min_keywords": str(MIN_KEYWORDS),
                "max_keywords": str(MAX_KEYWORDS),
                "allowed_tags": ", ".join(ALLOWED_TAGS),
            },
        )
        system_prompt = self._prompt_builder.build_system_prompt(
            "system",
            {"show_name": "Cast It", "language": article.language},
        )

        response = self._llm.chat(
            LLMRequest(system_prompt=system_prompt, user_prompt=user_prompt)
        )
        keywords = parse_keywords(
            response.content,
            minimum=MIN_KEYWORDS,
            maximum=MAX_KEYWORDS,
        )
        keywords = canonicalize_tags(keywords)[:MAX_KEYWORDS]
        extracted_at = timezone.now()

        self._save_keywords(article, keywords)
        article.keywords_generated_at = extracted_at
        article.save(update_fields=["keywords_generated_at", "updated_at"])

        elapsed = time.perf_counter() - started
        logger.info(
            "Keyword extraction completed",
            extra={
                "event": "keywords_completed",
                "article_id": str(article.id),
                "keyword_count": len(keywords),
                "elapsed_time": elapsed,
            },
        )

        return KeywordDTO(
            article_id=article.id,
            keywords=keywords,
            extracted_at=extracted_at,
        )

    @staticmethod
    def _save_keywords(article: Article, keywords: list[str]) -> None:
        # The taxonomy tags are authoritative: drop whatever the article had
        # (e.g. raw RSS categories) and keep only the extracted tags.
        ArticleTag.objects.filter(article=article).delete()
        for keyword in keywords:
            slug = slugify(keyword) or keyword.lower().replace(" ", "-")
            tag, _ = Tag.objects.get_or_create(
                slug=slug,
                defaults={"name": keyword},
            )
            ArticleTag.objects.get_or_create(article=article, tag=tag)


_ALLOWED_BY_KEY = {tag.lower(): tag for tag in ALLOWED_TAGS}


def canonicalize_tags(candidates: list[str]) -> list[str]:
    """Map free-form tag candidates onto the fixed taxonomy, dropping the rest."""
    canonical: list[str] = []
    for candidate in candidates:
        match = _ALLOWED_BY_KEY.get(candidate.strip().lower())
        if match and match not in canonical:
            canonical.append(match)
    return canonical
