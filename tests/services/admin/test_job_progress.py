"""Tests for operations job progress helpers."""

import pytest

from apps.episodes.models import Episode, EpisodeStatus
from apps.scheduler.models import Job, JobStatus, JobType
from services.admin.job_progress import JobProgressService


@pytest.mark.django_db
def test_find_active_script_job() -> None:
    episode = Episode.objects.create(title="Draft", status=EpisodeStatus.DRAFT)
    job = Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.RUNNING,
        progress=40,
        payload={"episode_id": str(episode.id)},
    )
    service = JobProgressService()
    found = service.find_active_script_job(str(episode.id))
    assert found is not None
    assert found.id == job.id


@pytest.mark.django_db
def test_serialize_job_marks_terminal() -> None:
    job = Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.SUCCEEDED,
        progress=100,
    )
    data = JobProgressService().serialize_job(job)
    assert data["label"] == "Script Generation"
    assert data["is_terminal"] is True
