"""Temporary workspace management for audio pipeline processing."""

import logging
import shutil
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


class TempWorkspace:
    """Episode-scoped temporary directory with idempotent cleanup."""

    def __init__(
        self,
        episode_id: uuid.UUID,
        *,
        base_dir: Path | None = None,
    ) -> None:
        self._episode_id = episode_id
        self._base_dir = base_dir
        self._path: Path | None = None
        self._cleaned = False

    @property
    def path(self) -> Path:
        if self._path is None:
            raise RuntimeError("TempWorkspace has not been entered.")
        return self._path

    def file(self, name: str) -> Path:
        """Return a path inside the workspace."""
        return self.path / name

    def __enter__(self) -> "TempWorkspace":
        prefix = f"episode_{self._episode_id}_"
        self._path = Path(tempfile.mkdtemp(prefix=prefix, dir=self._base_dir))
        logger.info(
            "Pipeline temp workspace created",
            extra={
                "event": "pipeline_temp_workspace_created",
                "episode_id": str(self._episode_id),
                "workspace_path": str(self._path),
            },
        )
        return self

    def __exit__(self, *args: object) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        """Remove the workspace directory if it exists."""
        if self._cleaned or self._path is None:
            return
        if self._path.exists():
            shutil.rmtree(self._path, ignore_errors=True)
            logger.info(
                "Pipeline temp workspace cleaned up",
                extra={
                    "event": "pipeline_temp_workspace_cleaned",
                    "episode_id": str(self._episode_id),
                    "workspace_path": str(self._path),
                },
            )
        self._cleaned = True
