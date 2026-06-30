"""Episode and job API tests."""

import pytest
from rest_framework.test import APIClient

from apps.episodes.models import Episode, EpisodeStatus
from apps.scheduler.models import Job, JobStatus, JobType

pytestmark = pytest.mark.django_db


@pytest.fixture
def episode(db: None) -> Episode:
    return Episode.objects.create(
        title="Weekly Show",
        status=EpisodeStatus.DRAFT,
        language="en",
    )


def test_list_episodes(api_client: APIClient, episode: Episode) -> None:
    response = api_client.get("/api/v1/episodes/")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_generate_script_action(
    api_client: APIClient,
    episode: Episode,
    mock_job_dispatch,
) -> None:
    del mock_job_dispatch
    response = api_client.post(f"/api/v1/episodes/{episode.id}/generate-script/")
    assert response.status_code == 202
    body = response.json()
    assert body["detail"] == "Script generation has been queued."
    assert Job.objects.filter(job_type=JobType.GENERATE_SCRIPT).exists()


def test_list_jobs(api_client: APIClient, db: None) -> None:
    Job.objects.create(job_type=JobType.HEALTH_CHECK, status=JobStatus.PENDING)
    response = api_client.get("/api/v1/jobs/")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_retrieve_job(api_client: APIClient, db: None) -> None:
    job = Job.objects.create(job_type=JobType.IMPORT_NEWS, status=JobStatus.QUEUED)
    response = api_client.get(f"/api/v1/jobs/{job.id}/")
    assert response.status_code == 200
    assert response.json()["job_type"] == JobType.IMPORT_NEWS
