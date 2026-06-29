"""Publisher factory for dependency injection."""

from apps.publish.models import Platform
from domain.publish.exceptions import PublishValidationError
from infrastructure.publish.providers.base import BasePublisher
from infrastructure.publish.providers.rss.publisher import RSSPublisher
from infrastructure.publish.providers.youtube.publisher import YouTubePublisher
from services.publish.settings import PublishSettings


class PublisherFactory:
    """Creates publisher instances for supported platforms."""

    def __init__(
        self,
        settings: PublishSettings | None = None,
        publishers: dict[str, BasePublisher] | None = None,
    ) -> None:
        self._settings = settings or PublishSettings.from_django_settings()
        self._publishers = publishers or self._default_publishers()

    def create(self, platform: str) -> BasePublisher:
        """Return a publisher for the requested platform."""
        publisher = self._publishers.get(platform)
        if publisher is None:
            raise PublishValidationError(f"No publisher registered for: {platform}")
        return publisher

    def all_publishers(self) -> dict[str, BasePublisher]:
        """Return all registered publishers."""
        return dict(self._publishers)

    def enabled_publishers(self) -> dict[str, BasePublisher]:
        """Return publishers for enabled platforms."""
        enabled = set(self._settings.enabled_platforms())
        return {
            platform: publisher
            for platform, publisher in self._publishers.items()
            if platform in enabled
        }

    def _default_publishers(self) -> dict[str, BasePublisher]:
        return {
            Platform.RSS: RSSPublisher(self._settings),
            Platform.YOUTUBE: YouTubePublisher(self._settings),
        }
