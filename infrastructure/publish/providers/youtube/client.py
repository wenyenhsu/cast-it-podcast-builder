"""YouTube API client adapter."""

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from domain.publish.exceptions import PublisherUnavailableError, YouTubePublishError
from services.publish.settings import PublishSettings

logger = logging.getLogger(__name__)

_TOKEN_URI = "https://oauth2.googleapis.com/token"
_YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
_UPLOAD_CHUNK_SIZE = 256 * 1024  # 256 KB


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


def _build_youtube_service(settings: PublishSettings):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=settings.youtube_refresh_token,
        token_uri=_TOKEN_URI,
        client_id=settings.youtube_client_id,
        client_secret=settings.youtube_client_secret,
        scopes=_YOUTUBE_SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


class DefaultYouTubeAPIClient:
    """YouTube API client using OAuth2 resumable upload."""

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
        if not self._settings.youtube_configured():
            raise PublisherUnavailableError(
                "YouTube publishing is unavailable or not configured."
            )

        try:
            from googleapiclient.http import MediaFileUpload

            svc = _build_youtube_service(self._settings)

            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description[:5000],
                    "tags": list(tags)[:500],
                    "categoryId": "22",  # People & Blogs
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False,
                },
            }

            # YouTube requires a video container — wrap MP3 in MP4 with black video
            with tempfile.TemporaryDirectory() as tmp_dir:
                mp4_path = Path(tmp_dir) / "episode.mp4"
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=1",
                        "-i", audio_file_path,
                        "-shortest",
                        "-c:v", "libx264", "-tune", "stillimage", "-crf", "35",
                        "-c:a", "aac", "-b:a", "192k",
                        str(mp4_path),
                    ],
                    check=True,
                    capture_output=True,
                )

                media = MediaFileUpload(
                    str(mp4_path),
                    mimetype="video/mp4",
                    resumable=True,
                    chunksize=_UPLOAD_CHUNK_SIZE,
                )

                request = svc.videos().insert(
                    part="snippet,status",
                    body=body,
                    media_body=media,
                )

                response = None
                while response is None:
                    _, response = request.next_chunk()

            video_id = response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            logger.info(
                "YouTube upload complete",
                extra={
                    "event": "youtube_upload_complete",
                    "video_id": video_id,
                    "channel_id": channel_id,
                    "title": title,
                },
            )
            return YouTubeUploadResult(video_id=video_id, video_url=video_url)

        except Exception as exc:
            logger.exception(
                "YouTube upload failed",
                extra={"event": "youtube_upload_failed", "title": title},
            )
            raise YouTubePublishError(f"YouTube upload failed: {exc}") from exc


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
