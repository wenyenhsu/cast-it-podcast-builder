"""Content hashing utility for duplicate detection."""

import hashlib
import re


class ContentHashService:
    """Generates SHA-256 hashes from normalized article content."""

    _WHITESPACE_PATTERN = re.compile(r"\s+")

    def normalize_content(self, content: str) -> str:
        """Normalize content by collapsing whitespace and lowercasing."""
        collapsed = self._WHITESPACE_PATTERN.sub(" ", content.strip())
        return collapsed.lower()

    def generate_hash(self, content: str, *, fallback_title: str = "") -> str:
        """Generate a SHA-256 hash from normalized content or title fallback."""
        normalized = self.normalize_content(content)
        if not normalized:
            normalized = self.normalize_content(fallback_title)

        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
