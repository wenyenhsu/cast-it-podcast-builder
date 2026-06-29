"""Tests for PublishSettings."""

from pathlib import Path

import pytest
from django.test import override_settings

from services.publish.settings import PublishSettings


@override_settings(
    YOUTUBE_CLIENT_ID="id",
    YOUTUBE_CLIENT_SECRET="secret",
    YOUTUBE_CHANNEL_ID="channel",
    ENABLE_YOUTUBE_PUBLISHING=True,
    ENABLE_RSS_PUBLISHING=True,
    RSS_FEED_OUTPUT_PATH="feeds/test.xml",
    MEDIA_ROOT="/tmp/media",
)
def test_from_django_settings() -> None:
    settings = PublishSettings.from_django_settings()
    assert settings.youtube_client_id == "id"
    assert settings.enable_youtube_publishing is True
    assert settings.enabled_platforms() == ("rss", "youtube")
    assert settings.youtube_configured() is True


def test_resolve_feed_output_path_relative(tmp_path: Path) -> None:
    settings = PublishSettings(
        youtube_api_key="",
        youtube_client_id="",
        youtube_client_secret="",
        youtube_channel_id="",
        enable_youtube_publishing=False,
        enable_rss_publishing=True,
        rss_feed_title="Test",
        rss_feed_subtitle="Sub",
        rss_feed_author="Author",
        rss_feed_language="en-us",
        rss_feed_site_url="https://example.com",
        rss_feed_audio_base_url="https://example.com/media",
        rss_feed_output_path="feeds/podcast.xml",
        media_root=tmp_path,
    )
    assert settings.resolve_feed_output_path() == tmp_path / "feeds" / "podcast.xml"


@pytest.mark.parametrize(
    ("youtube_enabled", "rss_enabled", "expected"),
    [
        (True, True, ("rss", "youtube")),
        (False, True, ("rss",)),
        (True, False, ("youtube",)),
        (False, False, ()),
    ],
)
def test_enabled_platforms(
    youtube_enabled: bool,
    rss_enabled: bool,
    expected: tuple[str, ...],
) -> None:
    settings = PublishSettings(
        youtube_api_key="",
        youtube_client_id="id" if youtube_enabled else "",
        youtube_client_secret="secret" if youtube_enabled else "",
        youtube_channel_id="channel" if youtube_enabled else "",
        enable_youtube_publishing=youtube_enabled,
        enable_rss_publishing=rss_enabled,
        rss_feed_title="Test",
        rss_feed_subtitle="Sub",
        rss_feed_author="Author",
        rss_feed_language="en-us",
        rss_feed_site_url="https://example.com",
        rss_feed_audio_base_url="https://example.com/media",
        rss_feed_output_path="feeds/podcast.xml",
        media_root=Path("/tmp"),
    )
    assert settings.enabled_platforms() == expected
