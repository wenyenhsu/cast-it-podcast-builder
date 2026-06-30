"""Log query integration points for the admin logs viewer."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class LogEntry:
    """Structured log entry for admin display."""

    timestamp: datetime
    severity: str
    message: str
    job_id: str = ""
    episode_id: str = ""
    provider: str = ""
    event: str = ""


class LogBackend(Protocol):
    """Protocol for pluggable log storage backends."""

    def query(
        self,
        *,
        search: str = "",
        severity: str = "",
        job_id: str = "",
        episode_id: str = "",
        provider: str = "",
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        """Return log entries matching the given filters."""


class InMemoryLogBackend:
    """Placeholder backend until centralized log storage is connected."""

    def query(self, **kwargs: Any) -> list[LogEntry]:
        del kwargs
        return []


class LogQueryService:
    """Admin-facing log query service with pluggable backend."""

    def __init__(self, backend: LogBackend | None = None) -> None:
        self._backend = backend or InMemoryLogBackend()

    def search(
        self,
        *,
        search: str = "",
        severity: str = "",
        job_id: str = "",
        episode_id: str = "",
        provider: str = "",
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        return self._backend.query(
            search=search,
            severity=severity,
            job_id=job_id,
            episode_id=episode_id,
            provider=provider,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
