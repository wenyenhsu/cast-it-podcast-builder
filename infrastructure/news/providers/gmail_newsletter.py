"""Gmail newsletter news provider (placeholder)."""

from typing import Any

from domain.dtos.article import ArticleDTO
from infrastructure.news.provider_config import ProviderConfig
from infrastructure.news.providers.base import BaseNewsProvider
from services.news.validation import ArticleValidator


class GmailNewsletterProvider(BaseNewsProvider):
    """Placeholder provider for Gmail newsletter ingestion.

    OAuth and mailbox access will be implemented in a future sprint.
    """

    def __init__(
        self,
        config: ProviderConfig,
        validator: ArticleValidator | None = None,
    ) -> None:
        super().__init__(config, validator)

    def collect(self) -> list[ArticleDTO]:
        raise NotImplementedError(
            "Gmail newsletter collection is not implemented yet. "
            "OAuth integration is required."
        )

    def normalize(self, raw_data: Any) -> list[ArticleDTO]:
        raise NotImplementedError(
            "Gmail newsletter normalization is not implemented yet."
        )

    def health_check(self) -> bool:
        raise NotImplementedError(
            "Gmail newsletter health check is not implemented yet."
        )
