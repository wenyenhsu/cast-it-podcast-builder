"""Publishing application settings."""

from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


@dataclass(frozen=True)
class PublishSettings:
    """Application-level publishing configuration loaded from environment."""

    youtube_api_key: str
    youtube_client_id: str
    youtube_client_secret: str
    youtube_channel_id: str
    enable_youtube_publishing: bool
    enable_rss_publishing: bool
    rss_feed_title: str
    rss_feed_subtitle: str
    rss_feed_author: str
    rss_feed_language: str
    rss_feed_site_url: str
    rss_feed_audio_base_url: str
    rss_feed_output_path: str
    media_root: Path

    @classmethod
    def from_django_settings(cls) -> "PublishSettings":
        """Load settings from Django configuration."""
        media_root = Path(getattr(settings, "MEDIA_ROOT", "media"))
        return cls(
            youtube_api_key=getattr(settings, "YOUTUBE_API_KEY", ""),
            youtube_client_id=getattr(settings, "YOUTUBE_CLIENT_ID", ""),
            youtube_client_secret=getattr(settings, "YOUTUBE_CLIENT_SECRET", ""),
            youtube_channel_id=getattr(settings, "YOUTUBE_CHANNEL_ID", ""),
            enable_youtube_publishing=getattr(
                settings,
                "ENABLE_YOUTUBE_PUBLISHING",
                False,
            ),
            enable_rss_publishing=getattr(settings, "ENABLE_RSS_PUBLISHING", True),
            rss_feed_title=getattr(settings, "RSS_FEED_TITLE", "Cast It Podcast"),
            rss_feed_subtitle=getattr(
                settings,
                "RSS_FEED_SUBTITLE",
                "AI-generated podcast episodes",
            ),
            rss_feed_author=getattr(settings, "RSS_FEED_AUTHOR", "Cast It"),
            rss_feed_language=getattr(settings, "RSS_FEED_LANGUAGE", "en-us"),
            rss_feed_site_url=getattr(
                settings,
                "RSS_FEED_SITE_URL",
                "https://example.com",
            ),
            rss_feed_audio_base_url=getattr(
                settings,
                "RSS_FEED_AUDIO_BASE_URL",
                "https://example.com/media",
            ),
            rss_feed_output_path=getattr(
                settings,
                "RSS_FEED_OUTPUT_PATH",
                "feeds/podcast.xml",
            ),
            media_root=media_root,
        )

    def resolve_feed_output_path(self) -> Path:
        """Return the absolute path for the RSS feed file."""
        output = Path(self.rss_feed_output_path)
        if output.is_absolute():
            return output
        return self.media_root / output

    def enabled_platforms(self) -> tuple[str, ...]:
        """Return platforms enabled for publishing."""
        platforms: list[str] = []
        if self.enable_rss_publishing:
            platforms.append("rss")
        if self.enable_youtube_publishing:
            platforms.append("youtube")
        return tuple(platforms)

    def youtube_configured(self) -> bool:
        """Return True when minimum YouTube credentials are present."""
        return bool(
            self.youtube_client_id
            and self.youtube_client_secret
            and self.youtube_channel_id
        )
