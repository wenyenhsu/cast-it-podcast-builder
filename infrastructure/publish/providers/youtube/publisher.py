"""YouTube publisher implementation."""

from apps.publish.models import Platform
from domain.publish.dtos import EpisodePublishContext, PublishMetadata, PublishResult
from domain.publish.exceptions import PublishValidationError, YouTubePublishError
from infrastructure.publish.providers.base import BasePublisher
from infrastructure.publish.providers.youtube.client import (
    DefaultYouTubeAPIClient,
    YouTubeAPIClient,
)
from services.publish.metadata_builder import PublishMetadataBuilder
from services.publish.settings import PublishSettings


class YouTubePublisher(BasePublisher):
    """Publishes episodes to YouTube via an API client adapter."""

    def __init__(
        self,
        settings: PublishSettings | None = None,
        client: YouTubeAPIClient | None = None,
        metadata_builder: PublishMetadataBuilder | None = None,
    ) -> None:
        self._settings = settings or PublishSettings.from_django_settings()
        self._client = client or DefaultYouTubeAPIClient(self._settings)
        self._metadata_builder = metadata_builder or PublishMetadataBuilder(
            self._settings
        )

    @property
    def platform(self) -> str:
        return Platform.YOUTUBE

    @classmethod
    def supported_platforms(cls) -> tuple[str, ...]:
        return (Platform.YOUTUBE,)

    def publish(
        self,
        context: EpisodePublishContext,
        metadata: PublishMetadata,
    ) -> PublishResult:
        self.validate(context, metadata)
        try:
            upload = self._client.upload_audio_episode(
                title=metadata.youtube.title,
                description=metadata.youtube.description,
                tags=metadata.youtube.tags,
                audio_file_path=str(context.audio_file_path),
                channel_id=self._settings.youtube_channel_id,
                privacy_status=metadata.youtube.privacy_status,
            )
        except YouTubePublishError:
            raise
        except Exception as exc:
            raise YouTubePublishError(f"YouTube publish failed: {exc}") from exc

        return PublishResult(
            platform=self.platform,
            published_url=upload.video_url,
            external_id=upload.video_id,
            metadata={
                "title": metadata.youtube.title,
                "tags": list(metadata.youtube.tags),
            },
        )

    def validate(
        self,
        context: EpisodePublishContext,
        metadata: PublishMetadata,
    ) -> None:
        if not self._settings.enable_youtube_publishing:
            raise PublishValidationError("YouTube publishing is disabled.")
        if not metadata.youtube.title.strip():
            raise PublishValidationError("YouTube title is required.")
        if not context.audio_file_path.exists():
            raise PublishValidationError(
                "YouTube publishing requires a local audio file."
            )

    def health_check(self) -> bool:
        return self._client.health_check()

    def build_metadata(self, context: EpisodePublishContext) -> PublishMetadata:
        return self._metadata_builder.build(context)
