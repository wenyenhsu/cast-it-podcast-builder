"""RSS feed news provider."""

import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Protocol

import feedparser  # type: ignore[import-untyped]
from feedparser import FeedParserDict

from domain.dtos.article import ArticleDTO
from infrastructure.news.provider_config import ProviderConfig
from infrastructure.news.providers.base import BaseNewsProvider
from services.news.validation import ArticleValidator

logger = logging.getLogger(__name__)


class FeedParserProtocol(Protocol):
    """Protocol for feedparser.parse to enable dependency injection in tests."""

    def __call__(self, url: str) -> FeedParserDict: ...


class RSSProvider(BaseNewsProvider):
    """Collects articles from an RSS or Atom feed."""

    def __init__(
        self,
        config: ProviderConfig,
        validator: ArticleValidator | None = None,
        feed_parser: FeedParserProtocol | None = None,
    ) -> None:
        super().__init__(config, validator)
        self._feed_parser = feed_parser or feedparser.parse
        self._rss_url = config.rss_url

    def collect(self) -> list[ArticleDTO]:
        if not self._rss_url:
            logger.error(
                "RSS URL is not configured",
                extra={
                    "event": "provider_error",
                    "provider": "RSSProvider",
                    "source": self.source_name,
                },
            )
            return []

        logger.info(
            "Provider started",
            extra={
                "event": "provider_started",
                "provider": "RSSProvider",
                "source": self.source_name,
                "rss_url": self._rss_url,
            },
        )

        raw_feed = self._feed_parser(self._rss_url)
        articles = self.normalize(raw_feed)

        logger.info(
            "Provider finished",
            extra={
                "event": "provider_finished",
                "provider": "RSSProvider",
                "source": self.source_name,
                "articles_collected": len(articles),
            },
        )
        return articles

    def normalize(self, raw_data: FeedParserDict) -> list[ArticleDTO]:
        articles: list[ArticleDTO] = []

        for entry in raw_data.get("entries", []):
            title = self._extract_title(entry)
            url = self._extract_url(entry)
            if not title and not url:
                continue

            articles.append(
                ArticleDTO(
                    title=title,
                    source=self.source_name,
                    url=url,
                    author=self._extract_author(entry),
                    published_at=self._extract_published_at(entry),
                    language=self.config.language,
                    category=self._extract_category(entry, raw_data),
                    summary=self._extract_summary(entry),
                    content=self._extract_content(entry),
                    tags=self._extract_tags(entry),
                )
            )

        return articles

    def health_check(self) -> bool:
        if not self._rss_url:
            return False

        try:
            feed = self._feed_parser(self._rss_url)
        except Exception:
            logger.exception(
                "RSS health check failed",
                extra={
                    "event": "health_check_failed",
                    "provider": "RSSProvider",
                    "source": self.source_name,
                },
            )
            return False

        return not feed.get("bozo", False) and bool(feed.get("feed"))

    @staticmethod
    def _extract_title(entry: FeedParserDict) -> str:
        return str(entry.get("title", "")).strip()

    @staticmethod
    def _extract_url(entry: FeedParserDict) -> str:
        link = entry.get("link") or entry.get("id") or ""
        return str(link).strip()

    @staticmethod
    def _extract_author(entry: FeedParserDict) -> str:
        author = entry.get("author") or ""
        if not author and entry.get("authors"):
            author = entry["authors"][0].get("name", "")
        return str(author).strip()

    @staticmethod
    def _extract_summary(entry: FeedParserDict) -> str:
        summary = entry.get("summary") or entry.get("description") or ""
        return str(summary).strip()

    @staticmethod
    def _extract_content(entry: FeedParserDict) -> str:
        content_list = entry.get("content")
        if content_list:
            return str(content_list[0].get("value", "")).strip()
        return RSSProvider._extract_summary(entry)

    @staticmethod
    def _extract_category(entry: FeedParserDict, feed: FeedParserDict) -> str:
        tags = entry.get("tags") or []
        if tags:
            return str(tags[0].get("term", "")).strip()

        feed_tags = feed.get("feed", {}).get("tags") or []
        if feed_tags:
            return str(feed_tags[0].get("term", "")).strip()

        return str(entry.get("category", "")).strip()

    @staticmethod
    def _extract_tags(entry: FeedParserDict) -> list[str]:
        tags: list[str] = []
        for tag in entry.get("tags") or []:
            term = str(tag.get("term", "")).strip()
            if term:
                tags.append(term)
        return tags

    @staticmethod
    def _extract_published_at(entry: FeedParserDict) -> datetime | None:
        published = entry.get("published") or entry.get("updated")
        if not published:
            parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            if parsed:
                try:
                    return datetime(
                        parsed[0],
                        parsed[1],
                        parsed[2],
                        parsed[3],
                        parsed[4],
                        parsed[5],
                        tzinfo=UTC,
                    )
                except (TypeError, ValueError, IndexError):
                    return None
            return None

        try:
            parsed_dt: datetime = parsedate_to_datetime(published)
            if parsed_dt.tzinfo is None:
                return parsed_dt.replace(tzinfo=UTC)
            return parsed_dt
        except (TypeError, ValueError):
            return None
