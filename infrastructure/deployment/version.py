"""Build and release version metadata."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class BuildMetadata:
    """Traceable build and release metadata."""

    version: str
    git_commit: str
    build_number: str
    environment: str
    release_timestamp: str
    image_tag: str

    def as_dict(self) -> dict[str, str]:
        return {
            "version": self.version,
            "git_commit": self.git_commit,
            "build_number": self.build_number,
            "environment": self.environment,
            "release_timestamp": self.release_timestamp,
            "image_tag": self.image_tag,
        }


def get_build_metadata() -> BuildMetadata:
    """Load build metadata from environment variables."""
    return BuildMetadata(
        version=os.getenv("APP_VERSION", "0.1.0"),
        git_commit=os.getenv("BUILD_GIT_COMMIT", "unknown"),
        build_number=os.getenv("BUILD_NUMBER", "local"),
        environment=os.getenv("ENVIRONMENT", "development"),
        release_timestamp=os.getenv(
            "BUILD_TIMESTAMP",
            datetime.now(tz=UTC).isoformat(),
        ),
        image_tag=os.getenv("IMAGE_TAG", "local"),
    )
