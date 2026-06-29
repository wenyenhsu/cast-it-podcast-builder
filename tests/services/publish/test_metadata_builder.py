"""Tests for PublishMetadataBuilder."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from domain.publish.dtos import EpisodePublishContext
from domain.publish.exceptions import InvalidPublishMetadataError
from services.publish.metadata_builder import PublishMetadataBuilder
from services.publish.settings import PublishSettings


@pytest.fixture
def builder(publish_settings: PublishSettings) -> PublishMetadataBuilder:
    return PublishMetadataBuilder(publish_settings)


@pytest.fixture
def context() -> EpisodePublishContext:
    episode_id = uuid4()
    return EpisodePublishContext(
        episode_id=episode_id,
        title="Weekly AI Roundup",
        description="Full episode description.",
        summary="Short summary about AI.",
        language="en",
        duration_seconds=600,
        publish_date=datetime(2026, 6, 29, tzinfo=UTC),
        cover_image="",
        audio_file_path=Path("/tmp/episode.mp3"),
        audio_url="https://podcast.test/media/episode.mp3",
        audio_format="mp3",
        audio_file_size=1024,
        audio_mime_type="audio/mpeg",
    )


def test_build_metadata(
    builder: PublishMetadataBuilder,
    context: EpisodePublishContext,
) -> None:
    metadata = builder.build(context)
    assert metadata.title == "Weekly AI Roundup"
    assert metadata.slug.startswith("weekly-ai-roundup-")
    assert "podcast" in metadata.tags
    assert metadata.rss_item.enclosure.url == context.audio_url
    assert metadata.youtube.title == "Weekly AI Roundup"
    assert "Short summary about AI." in metadata.youtube.description


def test_build_title_rejects_empty(builder: PublishMetadataBuilder) -> None:
    with pytest.raises(InvalidPublishMetadataError):
        builder.build_title("   ")


def test_build_slug_fallback(builder: PublishMetadataBuilder) -> None:
    slug = builder.build_slug("🎧", uuid4())
    assert slug.startswith("episode-")


def test_metadata_summary(
    builder: PublishMetadataBuilder,
    context: EpisodePublishContext,
) -> None:
    metadata = builder.build(context)
    summary = builder.build_metadata_summary(metadata)
    assert summary["title"] == metadata.title
    assert summary["duration_seconds"] == 600
