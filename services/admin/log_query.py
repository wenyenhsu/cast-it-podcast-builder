"""Log query integration points for the admin logs viewer."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from apps.observability.models import OperationalEvent
from apps.scheduler.models import Job, JobStatus
from services.admin.job_progress import JobProgressService


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
    """Empty backend for tests that should not hit the database."""

    def query(self, **kwargs: Any) -> list[LogEntry]:
        del kwargs
        return []


class DatabaseLogBackend:
    """Aggregates failed jobs and operational events for the operations UI."""

    @staticmethod
    def _normalize_severity(severity: str) -> str:
        return severity.strip().lower()

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
        entries: list[LogEntry] = []
        entries.extend(
            self._failed_job_entries(
                search=search,
                severity=severity,
                job_id=job_id,
                episode_id=episode_id,
                date_from=date_from,
                date_to=date_to,
            )
        )
        entries.extend(
            self._operational_event_entries(
                search=search,
                severity=severity,
                job_id=job_id,
                episode_id=episode_id,
                provider=provider,
                date_from=date_from,
                date_to=date_to,
            )
        )
        entries.sort(key=lambda item: item.timestamp, reverse=True)
        if search:
            needle = search.lower()
            entries = [
                entry
                for entry in entries
                if needle
                in " ".join(
                    [
                        entry.message,
                        entry.event,
                        entry.job_id,
                        entry.episode_id,
                        entry.provider,
                    ]
                ).lower()
            ]
        return entries[:limit]

    def _failed_job_entries(
        self,
        *,
        search: str,
        severity: str,
        job_id: str,
        episode_id: str,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[LogEntry]:
        if severity and self._normalize_severity(severity) != "error":
            return []

        jobs = Job.objects.filter(status=JobStatus.FAILED).order_by("-updated_at")
        if job_id:
            jobs = jobs.filter(pk=job_id)
        if episode_id:
            jobs = jobs.filter(payload__episode_id=episode_id)
        if date_from is not None:
            jobs = jobs.filter(updated_at__gte=date_from)
        if date_to is not None:
            jobs = jobs.filter(updated_at__lte=date_to)

        progress = JobProgressService()
        entries: list[LogEntry] = []
        for job in jobs[:200]:
            message = job.error_message or "Job failed."
            label = progress.label_for(job.job_type)
            if search:
                needle = search.lower()
                if (
                    needle not in message.lower()
                    and needle not in label.lower()
                    and needle not in job.job_type.lower()
                ):
                    continue
            payload = job.payload or {}
            entries.append(
                LogEntry(
                    timestamp=job.completed_at or job.updated_at,
                    severity="ERROR",
                    message=message,
                    job_id=str(job.id),
                    episode_id=str(payload.get("episode_id", "") or ""),
                    event=f"job.failed:{label}",
                )
            )
        return entries

    def _operational_event_entries(
        self,
        *,
        search: str,
        severity: str,
        job_id: str,
        episode_id: str,
        provider: str,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[LogEntry]:
        events = OperationalEvent.objects.all().order_by("-created_at")
        if severity:
            events = events.filter(severity=self._normalize_severity(severity))
        else:
            events = events.filter(severity__in=["error", "critical", "warning"])
        if job_id:
            events = events.filter(job_id=job_id)
        if episode_id:
            events = events.filter(episode_id=episode_id)
        if provider:
            events = events.filter(provider__icontains=provider)
        if date_from is not None:
            events = events.filter(created_at__gte=date_from)
        if date_to is not None:
            events = events.filter(created_at__lte=date_to)

        entries: list[LogEntry] = []
        for record in events[:200]:
            if search:
                needle = search.lower()
                haystack = " ".join(
                    [record.message, record.name, record.event_type, record.job_id]
                ).lower()
                if needle not in haystack:
                    continue
            entries.append(
                LogEntry(
                    timestamp=record.created_at,
                    severity=record.severity.upper(),
                    message=record.message,
                    job_id=record.job_id,
                    episode_id=record.episode_id,
                    provider=record.provider,
                    event=record.name or record.event_type,
                )
            )
        return entries


class LogQueryService:
    """Admin-facing log query service with pluggable backend."""

    def __init__(self, backend: LogBackend | None = None) -> None:
        self._backend = backend or DatabaseLogBackend()

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
