"""Web crawler news provider (placeholder)."""

from typing import Any

from domain.dtos.article import ArticleDTO
from infrastructure.news.provider_config import ProviderConfig
from infrastructure.news.providers.base import BaseNewsProvider
from services.news.validation import ArticleValidator


class WebCrawlerProvider(BaseNewsProvider):
    """Placeholder provider for web crawling-based news ingestion."""

    def __init__(
        self,
        config: ProviderConfig,
        validator: ArticleValidator | None = None,
    ) -> None:
        super().__init__(config, validator)

    def collect(self) -> list[ArticleDTO]:
        raise NotImplementedError("Web crawler collection is not implemented yet.")

    def normalize(self, raw_data: Any) -> list[ArticleDTO]:
        raise NotImplementedError("Web crawler normalization is not implemented yet.")

    def health_check(self) -> bool:
        raise NotImplementedError("Web crawler health check is not implemented yet.")
