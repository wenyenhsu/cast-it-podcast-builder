"""Tests for publishing providers."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from domain.publish.dtos import (
    EnclosureMetadata,
    EpisodePublishContext,
    PublishMetadata,
    RSSItemFields,
    YouTubeMetadataFields,
)
from domain.publish.exceptions import PublishValidationError, YouTubePublishError
from infrastructure.publish.providers.factory import PublisherFactory
from infrastructure.publish.providers.rss.publisher import RSSPublisher
from infrastructure.publish.providers.youtube.client import StubYouTubeAPIClient
from infrastructure.publish.providers.youtube.publisher import YouTubePublisher
from services.publish.settings import PublishSettings


@pytest.fixture
def publish_context() -> EpisodePublishContext:
    return EpisodePublishContext(
        episode_id=uuid4(),
        title="Episode Title",
        description="Episode description",
        summary="Summary",
        language="en",
        duration_seconds=300,
        publish_date=datetime(2026, 6, 29, tzinfo=UTC),
        cover_image="",
        audio_file_path=Path("/tmp/episode.mp3"),
        audio_url="https://podcast.test/media/episode.mp3",
        audio_format="mp3",
        audio_file_size=512,
        audio_mime_type="audio/mpeg",
    )


@pytest.fixture
def publish_metadata(publish_context: EpisodePublishContext) -> PublishMetadata:
    rss_item = RSSItemFields(
        title="Episode Title",
        description="Episode description",
        link="https://podcast.test/episodes/episode-title",
        guid="guid-1",
        pub_date=datetime(2026, 6, 29, tzinfo=UTC),
        enclosure=EnclosureMetadata(
            url=publish_context.audio_url,
            length=512,
            mime_type="audio/mpeg",
            duration_seconds=300,
        ),
        slug="episode-title",
    )
    return PublishMetadata(
        title="Episode Title",
        description="Episode description",
        summary="Summary",
        slug="episode-title",
        tags=("podcast", "ai"),
        language="en",
        duration_seconds=300,
        rss_item=rss_item,
        youtube=YouTubeMetadataFields(
            title="Episode Title",
            description="YouTube description",
            tags=("podcast",),
        ),
    )


def test_youtube_publisher_publish(
    publish_settings: PublishSettings,
    publish_context: EpisodePublishContext,
    publish_metadata: PublishMetadata,
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "episode.mp3"
    audio_path.write_bytes(b"audio")
    context = EpisodePublishContext(
        **{
            **publish_context.__dict__,
            "audio_file_path": audio_path,
        }
    )
    client = StubYouTubeAPIClient()
    publisher = YouTubePublisher(settings=publish_settings, client=client)
    result = publisher.publish(context, publish_metadata)
    assert result.platform == "youtube"
    assert result.external_id == "stub-video-id"
    assert len(client.upload_calls) == 1


def test_youtube_publisher_health_check(
    publish_settings: PublishSettings,
) -> None:
    publisher = YouTubePublisher(
        settings=publish_settings,
        client=StubYouTubeAPIClient(healthy=True),
    )
    assert publisher.health_check() is True


def test_youtube_publisher_upload_failure(
    publish_settings: PublishSettings,
    publish_context: EpisodePublishContext,
    publish_metadata: PublishMetadata,
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "episode.mp3"
    audio_path.write_bytes(b"audio")
    context = EpisodePublishContext(
        **{
            **publish_context.__dict__,
            "audio_file_path": audio_path,
        }
    )
    client = StubYouTubeAPIClient(fail=True)
    publisher = YouTubePublisher(settings=publish_settings, client=client)
    with pytest.raises(YouTubePublishError):
        publisher.publish(context, publish_metadata)


def test_rss_publisher_publish(
    publish_settings: PublishSettings,
    publish_context: EpisodePublishContext,
    publish_metadata: PublishMetadata,
) -> None:
    publisher = RSSPublisher(publish_settings)
    result = publisher.publish(publish_context, publish_metadata)
    assert result.platform == "rss"
    assert result.published_url.startswith("https://podcast.test/episodes/")


def test_rss_publisher_validation_rejects_missing_url(
    publish_settings: PublishSettings,
    publish_context: EpisodePublishContext,
    publish_metadata: PublishMetadata,
) -> None:
    broken_context = EpisodePublishContext(
        **{
            **publish_context.__dict__,
            "audio_url": "",
        }
    )
    publisher = RSSPublisher(publish_settings)
    with pytest.raises(PublishValidationError):
        publisher.publish(broken_context, publish_metadata)


def test_publisher_factory_create(
    publish_settings: PublishSettings,
) -> None:
    factory = PublisherFactory(publish_settings)
    assert factory.create("rss").platform == "rss"
    assert factory.create("youtube").platform == "youtube"
    with pytest.raises(PublishValidationError):
        factory.create("spotify")


def test_base_publisher_supported_platforms() -> None:
    assert RSSPublisher.supported_platforms() == ("rss",)
    assert YouTubePublisher.supported_platforms() == ("youtube",)
