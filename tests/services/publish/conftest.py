"""Shared fixtures for publishing service tests."""

from pathlib import Path

import pytest
from django.utils import timezone

from apps.articles.models import Article, ArticleStatus
from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import Episode, EpisodeArticle, EpisodeStatus
from apps.providers.models import NewsSource, ProviderType
from infrastructure.publish.providers.youtube.client import StubYouTubeAPIClient
from infrastructure.publish.providers.youtube.publisher import YouTubePublisher
from services.publish.settings import PublishSettings


@pytest.fixture
def publish_settings(tmp_path: Path) -> PublishSettings:
    media_root = tmp_path / "media"
    media_root.mkdir(parents=True, exist_ok=True)
    return PublishSettings(
        youtube_api_key="test-api-key",
        youtube_client_id="client-id",
        youtube_client_secret="client-secret",
        youtube_refresh_token="refresh-token",
        youtube_channel_id="channel-id",
        enable_youtube_publishing=True,
        enable_rss_publishing=True,
        rss_feed_title="Test Podcast",
        rss_feed_subtitle="Test subtitle",
        rss_feed_author="Test Author",
        rss_feed_language="en-us",
        rss_feed_site_url="https://podcast.test",
        rss_feed_audio_base_url="https://podcast.test/media",
        rss_feed_output_path="feeds/podcast.xml",
        media_root=media_root,
    )


@pytest.fixture
def publishable_episode(db: None, tmp_path: Path) -> Episode:
    episode = Episode.objects.create(
        title="Weekly AI Roundup",
        description="Episode about artificial intelligence news.",
        summary="AI news summary",
        language="en",
        status=EpisodeStatus.COMPLETED,
        duration_seconds=600,
        publish_date=timezone.now().date(),
    )
    source = NewsSource.objects.create(
        name="Publish Test Source",
        provider_type=ProviderType.RSS,
    )
    article = Article.objects.create(
        source=source,
        title="Publishable source article",
        url="https://example.com/publishable-source",
        content_hash=f"publishable-{episode.id}",
        status=ArticleStatus.SELECTED,
    )
    EpisodeArticle.objects.create(episode=episode, article=article)
    audio_path = tmp_path / "media" / "audio" / "episode-final.mp3"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"fake-audio-bytes")
    AudioAsset.objects.create(
        episode=episode,
        file_path=str(audio_path.relative_to(tmp_path / "media").as_posix()),
        duration=600,
        format="mp3",
        file_size=len(b"fake-audio-bytes"),
        is_final_episode_audio=True,
        status=AudioAssetStatus.READY,
    )
    return episode


@pytest.fixture
def youtube_publisher(
    publish_settings: PublishSettings,
) -> YouTubePublisher:
    client = StubYouTubeAPIClient()
    return YouTubePublisher(settings=publish_settings, client=client)
