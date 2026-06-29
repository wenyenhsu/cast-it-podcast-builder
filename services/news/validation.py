"""Article validation for news ingestion."""

from dataclasses import dataclass, field
from datetime import datetime

from django.utils import timezone

from domain.dtos.article import ArticleDTO


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating an ArticleDTO."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)


class ArticleValidator:
    """Validates normalized article DTOs before persistence."""

    def validate(self, article: ArticleDTO) -> ValidationResult:
        errors: list[str] = []

        if not article.title.strip():
            errors.append("Title must not be empty.")

        if not article.url.strip():
            errors.append("URL is required.")

        if article.published_at is not None and not self._is_valid_publish_date(
            article.published_at
        ):
            errors.append("Published date is invalid.")

        return ValidationResult(is_valid=not errors, errors=errors)

    @staticmethod
    def _is_valid_publish_date(published_at: datetime) -> bool:
        if published_at.tzinfo is None:
            return False

        now = timezone.now()
        return published_at <= now
