"""Episode pipeline stage inspection for admin views."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from apps.audio.models import AudioAsset, AudioAssetStatus, PipelineRun
from apps.episodes.models import Episode
from apps.publish.models import PublishJob
from apps.scheduler.models import Job


@dataclass(frozen=True)
class PipelineStage:
    """One stage in an episode pipeline."""

    name: str
    status: str
    duration_seconds: float | None
    started_at: datetime | None
    finished_at: datetime | None
    error: str


class EpisodePipelineService:
    """Builds pipeline stage data for an episode."""

    STAGE_NAMES = (
        "News Collection",
        "Summary",
        "Classification",
        "Ranking",
        "Script",
        "Audio",
        "Publishing",
    )

    def build_pipeline(self, episode: Episode) -> list[PipelineStage]:
        """Return ordered pipeline stages for an episode."""
        jobs = list(
            Job.objects.filter(payload__episode_id=str(episode.id)).order_by(
                "created_at"
            )
        )
        articles_count = episode.articles.count()
        latest_script = episode.scripts.order_by("-version").first()
        audio_assets = list(episode.audio_assets.all())
        publish_jobs = list(episode.publish_jobs.all())
        pipeline_runs = list(episode.pipeline_runs.all())

        return [
            self._news_collection_stage(episode, articles_count, jobs),
            self._generic_job_stage("Summary", jobs, "summarize_article"),
            self._generic_job_stage("Classification", jobs, "classify_article"),
            self._ranking_stage(episode, jobs),
            self._script_stage(latest_script, jobs),
            self._audio_stage(audio_assets, pipeline_runs, jobs),
            self._publishing_stage(publish_jobs, jobs),
        ]

    def _news_collection_stage(
        self,
        episode: Episode,
        articles_count: int,
        jobs: list[Job],
    ) -> PipelineStage:
        import_jobs = [j for j in jobs if j.job_type == "import_news"]
        job = import_jobs[-1] if import_jobs else None
        status = "completed" if articles_count else "pending"
        if job:
            status = job.status
        return PipelineStage(
            name="News Collection",
            status=status,
            duration_seconds=self._job_duration(job),
            started_at=job.started_at if job else None,
            finished_at=job.completed_at if job else None,
            error=job.error_message if job else "",
        )

    def _generic_job_stage(
        self,
        name: str,
        jobs: list[Job],
        job_type: str,
    ) -> PipelineStage:
        matching = [j for j in jobs if j.job_type == job_type]
        job = matching[-1] if matching else None
        return PipelineStage(
            name=name,
            status=job.status if job else "pending",
            duration_seconds=self._job_duration(job),
            started_at=job.started_at if job else None,
            finished_at=job.completed_at if job else None,
            error=job.error_message if job else "",
        )

    def _ranking_stage(self, episode: Episode, jobs: list[Job]) -> PipelineStage:
        planning = [j for j in jobs if j.job_type == "episode_planning"]
        job = planning[-1] if planning else None
        has_scores = episode.articles.filter(importance_score__isnull=False).exists()
        status = job.status if job else ("completed" if has_scores else "pending")
        return PipelineStage(
            name="Ranking",
            status=status,
            duration_seconds=self._job_duration(job),
            started_at=job.started_at if job else None,
            finished_at=job.completed_at if job else None,
            error=job.error_message if job else "",
        )

    def _script_stage(self, script, jobs: list[Job]) -> PipelineStage:
        script_jobs = [j for j in jobs if j.job_type == "generate_script"]
        job = script_jobs[-1] if script_jobs else None
        status = script.status if script else (job.status if job else "pending")
        return PipelineStage(
            name="Script",
            status=status,
            duration_seconds=self._job_duration(job),
            started_at=job.started_at if job else None,
            finished_at=job.completed_at if job else None,
            error=job.error_message if job else "",
        )

    def _audio_stage(
        self,
        assets: list[AudioAsset],
        pipeline_runs: list[PipelineRun],
        jobs: list[Job],
    ) -> PipelineStage:
        audio_jobs = [j for j in jobs if j.job_type == "generate_audio"]
        pipeline_jobs = [j for j in jobs if j.job_type == "run_audio_pipeline"]
        relevant_jobs = pipeline_jobs or audio_jobs
        job = relevant_jobs[-1] if relevant_jobs else None
        ready = any(a.status == AudioAssetStatus.READY for a in assets)
        run = pipeline_runs[-1] if pipeline_runs else None
        status = run.status if run else ("completed" if ready else "pending")
        if job:
            status = job.status
        return PipelineStage(
            name="Audio",
            status=status,
            duration_seconds=self._job_duration(job),
            started_at=job.started_at if job else None,
            finished_at=job.completed_at if job else None,
            error=job.error_message if job else "",
        )

    def _publishing_stage(
        self,
        publish_jobs: list[PublishJob],
        jobs: list[Job],
    ) -> PipelineStage:
        pub_jobs = [j for j in jobs if j.job_type == "publish_episode"]
        job = pub_jobs[-1] if pub_jobs else None
        latest = publish_jobs[-1] if publish_jobs else None
        status = latest.status if latest else (job.status if job else "pending")
        started_at = latest.started_at if latest else None
        if started_at is None and job is not None:
            started_at = job.started_at
        finished_at = latest.completed_at if latest else None
        if finished_at is None and job is not None:
            finished_at = job.completed_at
        error = latest.error_message if latest else ""
        if not error and job is not None:
            error = job.error_message
        return PipelineStage(
            name="Publishing",
            status=status,
            duration_seconds=self._job_duration(job),
            started_at=started_at,
            finished_at=finished_at,
            error=error,
        )

    def _job_duration(self, job: Job | None) -> float | None:
        if job is None or not job.started_at or not job.completed_at:
            return None
        return (job.completed_at - job.started_at).total_seconds()

    def as_dicts(self, episode: Episode) -> list[dict[str, Any]]:
        return [
            {
                "name": stage.name,
                "status": stage.status,
                "duration_seconds": stage.duration_seconds,
                "started_at": stage.started_at,
                "finished_at": stage.finished_at,
                "error": stage.error,
            }
            for stage in self.build_pipeline(episode)
        ]
