"""Job dispatch helpers for Django Admin actions."""

import logging
from typing import Any

from api.v1.services.job_dispatch import ApiJobDispatchService
from apps.scheduler.models import Job, JobType
from apps.scheduler.tasks.registry import get_task_for_job_type
from services.jobs.job_service import JobService

logger = logging.getLogger(__name__)


def _json_safe_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Coerce payload values to JSON-serializable primitives."""
    if not payload:
        return {}
    return {key: str(value) for key, value in payload.items() if value is not None}


class AdminJobDispatchService:
    """Dispatches background jobs from admin bulk actions."""

    def __init__(
        self,
        dispatch: ApiJobDispatchService | None = None,
        job_service: JobService | None = None,
    ) -> None:
        self._dispatch = dispatch or ApiJobDispatchService()
        self._jobs = job_service or JobService()

    def enqueue(self, job_type: str, payload: dict[str, Any] | None = None) -> Job:
        return self._dispatch.dispatch(job_type, _json_safe_payload(payload))

    def import_news(self, *, source_id: str | None = None) -> Job:
        payload: dict[str, Any] = {}
        if source_id:
            payload["source_id"] = source_id
        return self.enqueue(JobType.IMPORT_NEWS, payload)

    def health_check(self, *, source_id: str, provider_type: str) -> Job:
        return self.enqueue(
            JobType.HEALTH_CHECK,
            {"source_id": source_id, "provider_type": provider_type},
        )

    def summarize_article(self, article_id: str) -> Job:
        return self.enqueue(
            JobType.SUMMARIZE_ARTICLE,
            {"article_id": article_id},
        )

    def classify_article(self, article_id: str) -> Job:
        return self.enqueue(
            JobType.CLASSIFY_ARTICLE,
            {"article_id": article_id},
        )

    def plan_episode(self, episode_id: str) -> Job:
        return self.enqueue(JobType.EPISODE_PLANNING, {"episode_id": episode_id})

    def generate_script(self, episode_id: str, *, script_id: str | None = None) -> Job:
        payload: dict[str, str] = {"episode_id": episode_id}
        if script_id:
            payload["script_id"] = script_id
        return self.enqueue(JobType.GENERATE_SCRIPT, payload)

    def generate_audio(
        self,
        episode_id: str,
        *,
        script_id: str | None = None,
        audio_asset_id: str | None = None,
    ) -> Job:
        payload: dict[str, str] = {"episode_id": episode_id}
        if script_id:
            payload["script_id"] = script_id
        if audio_asset_id:
            payload["audio_asset_id"] = audio_asset_id
        return self.enqueue(JobType.GENERATE_AUDIO, payload)

    def run_audio_pipeline(
        self,
        episode_id: str,
        *,
        audio_asset_id: str | None = None,
    ) -> Job:
        payload: dict[str, str] = {"episode_id": episode_id}
        if audio_asset_id:
            payload["audio_asset_id"] = audio_asset_id
        return self.enqueue(JobType.RUN_AUDIO_PIPELINE, payload)

    def publish_episode(
        self,
        episode_id: str,
        *,
        platforms: list[str] | None = None,
    ) -> Job:
        payload: dict[str, Any] = {"episode_id": episode_id}
        if platforms:
            payload["platforms"] = platforms
        return self.enqueue(JobType.PUBLISH_EPISODE, payload)

    def retry_job(self, job: Job) -> Job:
        retried = self._jobs.retry_job(job)
        if get_task_for_job_type(retried.job_type) is not None:
            self._dispatch.redispatch(retried)
        return retried

    def cancel_job(self, job: Job) -> Job:
        return self._jobs.mark_cancelled(job)
