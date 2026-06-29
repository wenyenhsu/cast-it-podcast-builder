"""RSS publisher implementation."""

import logging

from apps.publish.models import Platform
from domain.publish.dtos import EpisodePublishContext, PublishMetadata, PublishResult
from domain.publish.exceptions import PublishValidationError
from infrastructure.publish.providers.base import BasePublisher
from services.publish.metadata_builder import PublishMetadataBuilder
from services.publish.settings import PublishSettings

logger = logging.getLogger(__name__)


class RSSPublisher(BasePublisher):
    """Publishes episodes by updating the podcast RSS feed."""

    def __init__(
        self,
        settings: PublishSettings | None = None,
        metadata_builder: PublishMetadataBuilder | None = None,
    ) -> None:
        self._settings = settings or PublishSettings.from_django_settings()
        self._metadata_builder = metadata_builder or PublishMetadataBuilder(
            self._settings
        )

    @property
    def platform(self) -> str:
        return Platform.RSS

    @classmethod
    def supported_platforms(cls) -> tuple[str, ...]:
        return (Platform.RSS,)

    def publish(
        self,
        context: EpisodePublishContext,
        metadata: PublishMetadata,
    ) -> PublishResult:
        self.validate(context, metadata)
        published_url = metadata.rss_item.link
        logger.info(
            "RSS episode metadata prepared",
            extra={
                "event": "rss_episode_prepared",
                "episode_id": str(context.episode_id),
                "published_url": published_url,
            },
        )
        return PublishResult(
            platform=self.platform,
            published_url=published_url,
            external_id=metadata.rss_item.guid,
            metadata={
                "rss_item": {
                    "title": metadata.rss_item.title,
                    "description": metadata.rss_item.description,
                    "link": metadata.rss_item.link,
                    "guid": metadata.rss_item.guid,
                    "slug": metadata.rss_item.slug,
                    "pub_date": metadata.rss_item.pub_date.isoformat(),
                    "enclosure_url": metadata.rss_item.enclosure.url,
                    "enclosure": {
                        "length": metadata.rss_item.enclosure.length,
                        "mime_type": metadata.rss_item.enclosure.mime_type,
                        "duration_seconds": (
                            metadata.rss_item.enclosure.duration_seconds
                        ),
                    },
                },
            },
        )

    def validate(
        self,
        context: EpisodePublishContext,
        metadata: PublishMetadata,
    ) -> None:
        if not self._settings.enable_rss_publishing:
            raise PublishValidationError("RSS publishing is disabled.")
        if not metadata.rss_item.enclosure.url:
            raise PublishValidationError("RSS enclosure URL is required.")
        if metadata.rss_item.enclosure.duration_seconds <= 0:
            raise PublishValidationError("RSS enclosure duration must be positive.")
        if not context.audio_url:
            raise PublishValidationError("RSS publishing requires an audio URL.")

    def health_check(self) -> bool:
        if not self._settings.enable_rss_publishing:
            return False
        output_path = self._settings.resolve_feed_output_path()
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            return output_path.parent.exists()
        except OSError:
            return False

    def build_metadata(self, context: EpisodePublishContext) -> PublishMetadata:
        return self._metadata_builder.build(context)
