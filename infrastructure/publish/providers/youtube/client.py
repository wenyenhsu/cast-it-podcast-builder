"""YouTube API client adapter."""

import logging
import uuid
from dataclasses import dataclass
from typing import Protocol

from domain.publish.exceptions import PublisherUnavailableError, YouTubePublishError
from services.publish.settings import PublishSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class YouTubeUploadResult:
    """Result returned by the YouTube API adapter."""

    video_id: str
    video_url: str


class YouTubeAPIClient(Protocol):
    """Protocol for YouTube upload operations."""

    def health_check(self) -> bool:
        """Verify YouTube credentials and API availability."""

    def upload_audio_episode(
        self,
        *,
        title: str,
        description: str,
        tags: tuple[str, ...],
        audio_file_path: str,
        channel_id: str,
        privacy_status: str = "public",
    ) -> YouTubeUploadResult:
        """Upload episode audio content to YouTube."""


class DefaultYouTubeAPIClient:
    """YouTube API adapter with structured boundaries for future API integration."""

    def __init__(self, settings: PublishSettings | None = None) -> None:
        self._settings = settings or PublishSettings.from_django_settings()

    def health_check(self) -> bool:
        if not self._settings.enable_youtube_publishing:
            return False
        if not self._settings.youtube_configured():
            logger.warning(
                "YouTube credentials are incomplete",
                extra={"event": "youtube_credentials_incomplete"},
            )
            return False
        return True

    def upload_audio_episode(
        self,
        *,
        title: str,
        description: str,
        tags: tuple[str, ...],
        audio_file_path: str,
        channel_id: str,
        privacy_status: str = "public",
    ) -> YouTubeUploadResult:
        if not self.health_check():
            raise PublisherUnavailableError(
                "YouTube publishing is unavailable or not configured."
            )

        del tags, audio_file_path, privacy_status

        # Placeholder upload path until full YouTube Data API integration lands.
        video_id = f"yt-{uuid.uuid4().hex[:11]}"
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(
            "YouTube upload simulated",
            extra={
                "event": "youtube_upload_simulated",
                "channel_id": channel_id,
                "title": title,
                "description_length": len(description),
                "video_id": video_id,
            },
        )
        return YouTubeUploadResult(video_id=video_id, video_url=video_url)


class StubYouTubeAPIClient:
    """Deterministic YouTube client for tests."""

    def __init__(
        self,
        *,
        healthy: bool = True,
        video_id: str = "stub-video-id",
        video_url: str = "https://www.youtube.com/watch?v=stub-video-id",
        fail: bool = False,
    ) -> None:
        self._healthy = healthy
        self._video_id = video_id
        self._video_url = video_url
        self._fail = fail
        self.upload_calls: list[dict[str, object]] = []

    def health_check(self) -> bool:
        return self._healthy

    def upload_audio_episode(
        self,
        *,
        title: str,
        description: str,
        tags: tuple[str, ...],
        audio_file_path: str,
        channel_id: str,
        privacy_status: str = "public",
    ) -> YouTubeUploadResult:
        self.upload_calls.append(
            {
                "title": title,
                "description": description,
                "tags": tags,
                "audio_file_path": audio_file_path,
                "channel_id": channel_id,
                "privacy_status": privacy_status,
            }
        )
        if self._fail:
            raise YouTubePublishError("Stub YouTube upload failure.")
        return YouTubeUploadResult(video_id=self._video_id, video_url=self._video_url)
