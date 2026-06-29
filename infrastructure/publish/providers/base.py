"""Base publisher interface."""

from abc import ABC, abstractmethod

from domain.publish.dtos import EpisodePublishContext, PublishMetadata, PublishResult


class BasePublisher(ABC):
    """Abstract adapter that every publishing target must implement."""

    @property
    @abstractmethod
    def platform(self) -> str:
        """Return the platform identifier."""

    @classmethod
    @abstractmethod
    def supported_platforms(cls) -> tuple[str, ...]:
        """Return platform identifiers handled by this publisher."""

    @abstractmethod
    def publish(
        self,
        context: EpisodePublishContext,
        metadata: PublishMetadata,
    ) -> PublishResult:
        """Publish episode content to the target platform."""

    @abstractmethod
    def validate(
        self,
        context: EpisodePublishContext,
        metadata: PublishMetadata,
    ) -> None:
        """Validate publish prerequisites for this platform."""

    @abstractmethod
    def health_check(self) -> bool:
        """Verify the publishing target is reachable and configured."""

    @abstractmethod
    def build_metadata(self, context: EpisodePublishContext) -> PublishMetadata:
        """Build platform-ready metadata for the episode."""
