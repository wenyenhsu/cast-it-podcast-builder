"""Publishing domain exceptions."""


class PublishError(Exception):
    """Base exception for publishing operations."""


class PublisherUnavailableError(PublishError):
    """Raised when a publishing target is unreachable or disabled."""


class InvalidPublishMetadataError(PublishError):
    """Raised when episode metadata cannot be built for publishing."""


class PublishValidationError(PublishError):
    """Raised when an episode fails pre-publish validation."""


class YouTubePublishError(PublishError):
    """Raised when YouTube publishing fails."""


class RSSPublishError(PublishError):
    """Raised when RSS publishing fails."""


class FeedGenerationError(PublishError):
    """Raised when RSS feed XML generation fails."""
