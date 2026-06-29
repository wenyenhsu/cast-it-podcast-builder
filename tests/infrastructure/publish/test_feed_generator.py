"""Tests for RSS feed generation."""

from datetime import UTC, datetime

import pytest

from apps.episodes.models import Episode
from apps.publish.models import Platform, PublishedEpisode
from infrastructure.publish.feed_generator import RSSFeedGenerator
from services.publish.settings import PublishSettings


@pytest.fixture
def feed_generator(publish_settings: PublishSettings) -> RSSFeedGenerator:
    return RSSFeedGenerator(publish_settings)


def test_generate_feed_xml(
    feed_generator: RSSFeedGenerator,
    publishable_episode: Episode,
) -> None:
    PublishedEpisode.objects.create(
        episode=publishable_episode,
        platform=Platform.RSS,
        published_url="https://podcast.test/episodes/weekly-ai-roundup",
        external_id="guid-123",
        published_at=datetime(2026, 6, 29, tzinfo=UTC),
        metadata={
            "rss_item": {
                "title": publishable_episode.title,
                "description": publishable_episode.description,
                "link": "https://podcast.test/episodes/weekly-ai-roundup",
                "guid": "guid-123",
                "slug": "weekly-ai-roundup",
                "pub_date": "2026-06-29T00:00:00+00:00",
                "enclosure_url": "https://podcast.test/media/episode.mp3",
                "enclosure": {
                    "length": 1024,
                    "mime_type": "audio/mpeg",
                    "duration_seconds": 600,
                },
            }
        },
    )
    xml = feed_generator.generate()
    assert "<rss" in xml
    assert "Weekly AI Roundup" in xml
    assert "audio/mpeg" in xml
    assert "https://podcast.test/media/episode.mp3" in xml


def test_write_feed_creates_file(
    feed_generator: RSSFeedGenerator,
    publish_settings: PublishSettings,
) -> None:
    path = feed_generator.write_feed(episodes=[])
    assert path == publish_settings.resolve_feed_output_path()
    assert path.exists()
    assert "<rss" in path.read_text(encoding="utf-8")


def test_generate_empty_feed(feed_generator: RSSFeedGenerator) -> None:
    xml = feed_generator.generate(episodes=[])
    assert "Test Podcast" in xml
