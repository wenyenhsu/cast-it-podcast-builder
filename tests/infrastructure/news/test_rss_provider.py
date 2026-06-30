"""Tests for RSS provider normalization."""

from datetime import UTC, datetime

from domain.dtos.article import ArticleDTO
from infrastructure.news.provider_config import ProviderConfig
from infrastructure.news.providers.rss import RSSProvider


def _sample_feed() -> dict[str, object]:
    return {
        "feed": {"tags": [{"term": "Technology"}]},
        "entries": [
            {
                "title": "  First Article  ",
                "link": "https://example.com/first",
                "author": "Jane Doe",
                "published": "Mon, 01 Jan 2024 12:00:00 GMT",
                "summary": "Summary text",
                "content": [{"value": "Full article body"}],
                "tags": [{"term": "AI"}, {"term": "News"}],
            },
            {
                "title": "",
                "link": "",
            },
        ],
    }


class TestRSSProvider:
    def setup_method(self) -> None:
        self.config = ProviderConfig(
            source_name="Example Feed",
            provider_type="rss",
            language="en",
            rss_url="https://example.com/rss",
        )

    def test_normalize_converts_feed_entries_to_dto(self) -> None:
        provider = RSSProvider(self.config, feed_parser=lambda _: _sample_feed())  # type: ignore[arg-type]
        articles = provider.normalize(_sample_feed())  # type: ignore[arg-type]

        assert len(articles) == 1
        article = articles[0]
        assert isinstance(article, ArticleDTO)
        assert article.title == "First Article"
        assert article.url == "https://example.com/first"
        assert article.author == "Jane Doe"
        assert article.source == "Example Feed"
        assert article.summary == "Summary text"
        assert article.content == "Full article body"
        assert article.category == "AI"
        assert article.tags == ["AI", "News"]
        assert article.published_at == datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

    def test_collect_uses_injected_feed_parser(self) -> None:
        provider = RSSProvider(self.config, feed_parser=lambda _: _sample_feed())  # type: ignore[arg-type]
        articles = provider.collect()
        assert len(articles) == 1

    def test_health_check_returns_true_for_valid_feed(self) -> None:
        provider = RSSProvider(
            self.config,
            feed_parser=lambda _: {"bozo": False, "feed": {"title": "Feed"}},
        )
        assert provider.health_check() is True

    def test_health_check_returns_false_for_broken_feed(self) -> None:
        provider = RSSProvider(
            self.config,
            feed_parser=lambda _: {"bozo": True, "feed": {}},
        )
        assert provider.health_check() is False

    def test_collect_returns_empty_when_rss_url_missing(self) -> None:
        config = ProviderConfig(source_name="No URL", provider_type="rss")
        provider = RSSProvider(config)
        assert provider.collect() == []

    def test_normalize_limits_articles_when_configured(self) -> None:
        feed = {
            "feed": {},
            "entries": [
                {"title": f"Article {index}", "link": f"https://example.com/{index}"}
                for index in range(5)
            ],
        }
        config = ProviderConfig(
            source_name="Limited Feed",
            provider_type="rss",
            max_articles_per_import=3,
        )
        provider = RSSProvider(config)
        articles = provider.normalize(feed)  # type: ignore[arg-type]
        assert len(articles) == 3
        assert articles[0].title == "Article 0"
