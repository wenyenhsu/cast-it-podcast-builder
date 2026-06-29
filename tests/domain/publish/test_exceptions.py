"""Tests for publishing domain exceptions."""

from domain.publish.exceptions import (
    FeedGenerationError,
    InvalidPublishMetadataError,
    PublishError,
    PublisherUnavailableError,
    PublishValidationError,
    RSSPublishError,
    YouTubePublishError,
)


def test_exception_hierarchy() -> None:
    assert issubclass(PublishValidationError, PublishError)
    assert issubclass(YouTubePublishError, PublishError)
    assert issubclass(RSSPublishError, PublishError)
    assert issubclass(FeedGenerationError, PublishError)
    assert issubclass(PublisherUnavailableError, PublishError)
    assert issubclass(InvalidPublishMetadataError, PublishError)
