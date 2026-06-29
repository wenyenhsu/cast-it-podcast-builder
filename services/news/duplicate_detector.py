"""Duplicate article detection."""

import logging

from django.db import models

from apps.articles.models import Article

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """Detects duplicate articles by content hash or URL."""

    def is_duplicate(self, *, content_hash: str, url: str) -> bool:
        """Return True when an article with the same hash or URL exists."""
        is_dup = Article.objects.filter(
            models.Q(content_hash=content_hash) | models.Q(url=url)
        ).exists()

        if is_dup:
            logger.info(
                "Duplicate article detected",
                extra={
                    "event": "duplicate_detected",
                    "content_hash": content_hash,
                    "url": url,
                },
            )

        return is_dup
