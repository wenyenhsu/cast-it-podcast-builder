"""Operational event model and service tests."""

import pytest

from domain.observability.dtos import OperationalEventDTO
from domain.observability.enums import EventSeverity
from services.observability.events import OperationalEventService


@pytest.mark.django_db
def test_record_and_query_event() -> None:
    service = OperationalEventService()
    created = service.record(
        OperationalEventDTO(
            event_type="job",
            severity=EventSeverity.ERROR,
            source="jobs",
            name="job_failed",
            message="Job failed unexpectedly",
            correlation_id="corr-1",
            job_id="job-1",
        )
    )
    assert created.id is not None
    events = service.list_events(job_id="job-1")
    assert len(events) == 1
    assert events[0].message == "Job failed unexpectedly"


@pytest.mark.django_db
def test_get_event_by_id() -> None:
    service = OperationalEventService()
    created = service.record(
        OperationalEventDTO(
            event_type="workflow",
            severity=EventSeverity.INFO,
            source="workflow",
            name="step_completed",
            message="Step completed",
        )
    )
    fetched = service.get(created.id)  # type: ignore[arg-type]
    assert fetched is not None
    assert fetched.name == "step_completed"
