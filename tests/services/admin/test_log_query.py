"""Tests for operations log query backend."""

import pytest

from apps.scheduler.models import Job, JobStatus, JobType
from services.admin.log_query import DatabaseLogBackend, LogQueryService
from services.observability.events import OperationalEventService
from domain.observability.dtos import OperationalEventDTO
from domain.observability.enums import EventSeverity


@pytest.mark.django_db
def test_database_log_backend_includes_failed_jobs() -> None:
    job = Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.FAILED,
        error_message="Ollama timed out",
        payload={"episode_id": "ep-1"},
    )

    entries = DatabaseLogBackend().query(severity="ERROR", limit=10)

    assert len(entries) == 1
    assert entries[0].message == "Ollama timed out"
    assert entries[0].job_id == str(job.id)
    assert entries[0].episode_id == "ep-1"
    assert entries[0].severity == "ERROR"


@pytest.mark.django_db
def test_database_log_backend_includes_operational_events() -> None:
    Job.objects.create(
        job_type=JobType.GENERATE_AUDIO,
        status=JobStatus.FAILED,
        error_message="TTS failed",
    )
    OperationalEventService().record(
        OperationalEventDTO(
            event_type="job",
            severity=EventSeverity.ERROR,
            source="worker",
            name="audio_synthesis_failed",
            message="Chatterbox connection refused",
            job_id="job-xyz",
        )
    )

    entries = LogQueryService().search(limit=20)

    assert len(entries) >= 2
    messages = {entry.message for entry in entries}
    assert "TTS failed" in messages
    assert "Chatterbox connection refused" in messages
