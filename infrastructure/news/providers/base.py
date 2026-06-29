"""Base news provider interface."""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from domain.dtos.article import ArticleDTO
from infrastructure.news.provider_config import ProviderConfig

if TYPE_CHECKING:
    from services.news.validation import ArticleValidator

logger = logging.getLogger(__name__)


class BaseNewsProvider(ABC):
    """Abstract adapter that every news source provider must implement."""

    def __init__(
        self,
        config: ProviderConfig,
        validator: "ArticleValidator | None" = None,
    ) -> None:
        self.config = config
        if validator is None:
            from services.news.validation import ArticleValidator as ValidatorClass

            validator = ValidatorClass()
        self._validator = validator

    @property
    def source_name(self) -> str:
        return self.config.source_name

    @abstractmethod
    def collect(self) -> list[ArticleDTO]:
        """Fetch raw data and return normalized articles."""

    @abstractmethod
    def normalize(self, raw_data: Any) -> list[ArticleDTO]:
        """Convert provider-specific raw data into ArticleDTO instances."""

    def validate(self, article: ArticleDTO) -> bool:
        """Validate a single article DTO."""
        result = self._validator.validate(article)
        if not result.is_valid:
            logger.warning(
                "Article validation failed",
                extra={
                    "event": "validation_failure",
                    "provider": self.__class__.__name__,
                    "source": article.source,
                    "url": article.url,
                    "errors": result.errors,
                },
            )
        return bool(result.is_valid)

    @abstractmethod
    def health_check(self) -> bool:
        """Verify the provider can reach its data source."""
