"""Operational event persistence and querying."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from domain.observability.dtos import OperationalEventDTO
from domain.observability.enums import EventSeverity


class OperationalEventService:
    """Persist and query operational events for troubleshooting."""

    def record(self, event: OperationalEventDTO) -> OperationalEventDTO:
        from apps.observability.models import OperationalEvent

        record = OperationalEvent.objects.create(
            event_type=event.event_type,
            severity=event.severity.value,
            source=event.source,
            name=event.name,
            message=event.message,
            correlation_id=event.correlation_id,
            request_id=event.request_id,
            job_id=event.job_id,
            workflow_run_id=event.workflow_run_id,
            episode_id=event.episode_id,
            provider=event.provider,
            duration_ms=event.duration_ms,
            payload=event.payload,
        )
        return self._to_dto(record)

    def get(self, event_id: UUID) -> OperationalEventDTO | None:
        from apps.observability.models import OperationalEvent

        record = OperationalEvent.objects.filter(id=event_id).first()
        if record is None:
            return None
        return self._to_dto(record)

    def list_events(
        self,
        *,
        event_type: str = "",
        severity: str = "",
        correlation_id: str = "",
        job_id: str = "",
        workflow_run_id: str = "",
        episode_id: str = "",
        provider: str = "",
        search: str = "",
        limit: int = 100,
    ) -> list[OperationalEventDTO]:
        from django.db.models import Q

        from apps.observability.models import OperationalEvent

        queryset = OperationalEvent.objects.all().order_by("-created_at")
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if severity:
            queryset = queryset.filter(severity=severity)
        if correlation_id:
            queryset = queryset.filter(correlation_id=correlation_id)
        if job_id:
            queryset = queryset.filter(job_id=job_id)
        if workflow_run_id:
            queryset = queryset.filter(workflow_run_id=workflow_run_id)
        if episode_id:
            queryset = queryset.filter(episode_id=episode_id)
        if provider:
            queryset = queryset.filter(provider=provider)
        if search:
            queryset = queryset.filter(
                Q(message__icontains=search) | Q(name__icontains=search)
            )
        return [self._to_dto(record) for record in queryset[:limit]]

    def record_from_log(
        self,
        *,
        event_type: str,
        severity: EventSeverity,
        source: str,
        name: str,
        message: str,
        **fields: Any,
    ) -> OperationalEventDTO:
        from infrastructure.observability.context import get_request_context

        ctx = get_request_context()
        return self.record(
            OperationalEventDTO(
                event_type=event_type,
                severity=severity,
                source=source,
                name=name,
                message=message,
                correlation_id=ctx.correlation_id,
                request_id=ctx.request_id,
                job_id=fields.get("job_id", ctx.job_id),
                workflow_run_id=fields.get("workflow_run_id", ctx.workflow_run_id),
                episode_id=fields.get("episode_id", ctx.episode_id),
                provider=fields.get("provider", ""),
                duration_ms=fields.get("duration_ms"),
                payload=fields.get("payload", {}),
            )
        )

    @staticmethod
    def _to_dto(record: Any) -> OperationalEventDTO:
        return OperationalEventDTO(
            id=record.id,
            event_type=record.event_type,
            severity=EventSeverity(record.severity),
            source=record.source,
            name=record.name,
            message=record.message,
            correlation_id=record.correlation_id,
            request_id=record.request_id,
            job_id=record.job_id,
            workflow_run_id=record.workflow_run_id,
            episode_id=record.episode_id,
            provider=record.provider,
            duration_ms=record.duration_ms,
            payload=record.payload,
            created_at=record.created_at,
        )

    @staticmethod
    def dto_to_dict(event: OperationalEventDTO) -> dict[str, Any]:
        return {
            "id": str(event.id) if event.id else None,
            "event_type": event.event_type,
            "severity": event.severity.value,
            "source": event.source,
            "name": event.name,
            "message": event.message,
            "correlation_id": event.correlation_id,
            "request_id": event.request_id,
            "job_id": event.job_id,
            "workflow_run_id": event.workflow_run_id,
            "episode_id": event.episode_id,
            "provider": event.provider,
            "duration_ms": event.duration_ms,
            "payload": event.payload,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
