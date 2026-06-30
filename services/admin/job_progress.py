"""Background job progress helpers for the operations dashboard."""

from typing import Any

from apps.scheduler.models import Job, JobStatus, JobType

ACTIVE_JOB_STATUSES = frozenset(
    {
        JobStatus.PENDING,
        JobStatus.QUEUED,
        JobStatus.RUNNING,
        JobStatus.RETRYING,
    }
)

JOB_TYPE_LABELS = {
    JobType.GENERATE_SCRIPT: "Script Generation",
    JobType.GENERATE_AUDIO: "TTS Audio",
    JobType.RUN_AUDIO_PIPELINE: "Audio Pipeline",
    JobType.IMPORT_NEWS: "News Import",
    JobType.EPISODE_PLANNING: "Episode Planning",
    JobType.PUBLISH_EPISODE: "Publishing",
}


class JobProgressService:
    """Serializes job state for operations UI polling."""

    def label_for(self, job_type: str) -> str:
        return JOB_TYPE_LABELS.get(job_type, job_type.replace("_", " ").title())

    def is_terminal(self, status: str) -> bool:
        return status in {
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }

    def find_active_script_job(self, episode_id: str) -> Job | None:
        if not episode_id:
            return None
        return (
            Job.objects.filter(
                job_type=JobType.GENERATE_SCRIPT,
                status__in=ACTIVE_JOB_STATUSES,
                payload__episode_id=episode_id,
            )
            .order_by("-created_at")
            .first()
        )

    def serialize_job(self, job: Job) -> dict[str, Any]:
        return {
            "id": str(job.id),
            "job_type": job.job_type,
            "label": self.label_for(job.job_type),
            "status": job.status,
            "progress": job.progress,
            "status_message": self.status_message(job),
            "error_message": job.error_message,
            "result": job.result,
            "is_terminal": self.is_terminal(job.status),
            "episode_id": job.payload.get("episode_id", ""),
            "script_id": job.payload.get("script_id", ""),
        }

    def status_message(self, job: Job) -> str:
        if job.error_message and job.status in {JobStatus.FAILED, JobStatus.RETRYING}:
            return job.error_message
        messages = {
            JobStatus.PENDING: "Preparing job...",
            JobStatus.QUEUED: "Waiting for worker...",
            JobStatus.RUNNING: self._running_message(job.job_type),
            JobStatus.RETRYING: "Retrying after a temporary error...",
            JobStatus.SUCCEEDED: "Completed successfully.",
            JobStatus.FAILED: job.error_message or "Job failed.",
            JobStatus.CANCELLED: "Job was cancelled.",
        }
        return messages.get(job.status, job.status)

    @staticmethod
    def _running_message(job_type: str) -> str:
        if job_type == JobType.GENERATE_SCRIPT:
            return "Generating script with LLM..."
        if job_type == JobType.GENERATE_AUDIO:
            return "Synthesizing TTS audio..."
        return "Running..."
