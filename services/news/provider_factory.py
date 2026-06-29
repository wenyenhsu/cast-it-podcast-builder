"""Factory for creating news provider instances."""

from apps.providers.models import NewsSource, ProviderType
from infrastructure.news.provider_config import ProviderConfig
from infrastructure.news.providers.base import BaseNewsProvider
from infrastructure.news.providers.gmail_newsletter import GmailNewsletterProvider
from infrastructure.news.providers.news_api import NewsAPIProvider
from infrastructure.news.providers.rss import RSSProvider
from infrastructure.news.providers.web_crawler import WebCrawlerProvider
from services.news.validation import ArticleValidator


class ProviderFactory:
    """Creates news provider adapters from NewsSource configuration."""

    _PROVIDER_MAP: dict[str, type[BaseNewsProvider]] = {
        ProviderType.RSS: RSSProvider,
        ProviderType.HTML: WebCrawlerProvider,
        ProviderType.API: NewsAPIProvider,
        ProviderType.MANUAL: GmailNewsletterProvider,
    }

    def __init__(self, validator: ArticleValidator | None = None) -> None:
        self._validator = validator or ArticleValidator()

    def create(self, source: NewsSource) -> BaseNewsProvider:
        """Build a provider adapter for the given news source."""
        provider_class = self._PROVIDER_MAP.get(
            source.provider_type,
            RSSProvider,
        )

        config = ProviderConfig(
            source_name=source.name,
            provider_type=source.provider_type,
            language=source.language,
            rss_url=source.rss_url,
            homepage=source.homepage,
        )
        return provider_class(config=config, validator=self._validator)
