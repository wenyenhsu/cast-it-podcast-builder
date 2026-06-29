"""News provider adapters."""

from infrastructure.news.providers.base import BaseNewsProvider
from infrastructure.news.providers.gmail_newsletter import GmailNewsletterProvider
from infrastructure.news.providers.news_api import NewsAPIProvider
from infrastructure.news.providers.rss import RSSProvider
from infrastructure.news.providers.web_crawler import WebCrawlerProvider

__all__ = [
    "BaseNewsProvider",
    "GmailNewsletterProvider",
    "NewsAPIProvider",
    "RSSProvider",
    "WebCrawlerProvider",
]
