"""Episode pipeline stage inspection for admin views."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from apps.audio.models import AudioAsset, AudioAssetStatus, PipelineRun
from apps.episodes.models import Episode
from apps.publish.models import PublishJob
from apps.scheduler.models import Job, JobStatus

SUCCESS_STATUSES = frozenset(
    {
        JobStatus.SUCCEEDED,
        "succeeded",
        "completed",
        "ready",
        "approved",
        "processed",
        "collected",
    }
)
RUNNING_STATUSES = frozenset(
    {
        JobStatus.RUNNING,
        JobStatus.RETRYING,
        JobStatus.QUEUED,
        "running",
        "retrying",
        "queued",
        "generating",
        "generating_script",
        "generating_audio",
        "collecting",
        "publishing",
    }
)
FAILED_STATUSES = frozenset(
    {
        JobStatus.FAILED,
        JobStatus.CANCELLED,
        "failed",
        "cancelled",
    }
)

STAGE_DESCRIPTIONS = {
    "News Collection": "Articles linked to this episode for script source material.",
    "Summary": "Article summaries generated for script input.",
    "Classification": "Articles categorized for editorial ranking.",
    "Ranking": "Articles scored by importance for script selection.",
    "Script": "Podcast dialogue script generated from selected sources.",
    "Audio": "TTS audio synthesized from the approved script.",
    "Publishing": "Episode distributed to configured platforms.",
}


@dataclass(frozen=True)
class PipelineStage:
    """One stage in an episode pipeline."""

    name: str
    status: str
    display_status: str
    duration_seconds: float | None
    duration_label: str
    started_at: datetime | None
    finished_at: datetime | None
    error: str
    description: str
    items_count: int | None


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
        articles = list(episode.articles.all())
        articles_count = len(articles)
        latest_script = episode.scripts.order_by("-version").first()
        audio_assets = list(episode.audio_assets.all())
        publish_jobs = list(episode.publish_jobs.all())
        pipeline_runs = list(episode.pipeline_runs.all())

        return [
            self._news_collection_stage(episode, articles_count, jobs),
            self._generic_job_stage(
                "Summary",
                jobs,
                "summarize_article",
                items=self._summarized_count(articles),
            ),
            self._generic_job_stage(
                "Classification",
                jobs,
                "classify_article",
                items=self._classified_count(articles),
            ),
            self._ranking_stage(episode, jobs, articles),
            self._script_stage(latest_script, jobs),
            self._audio_stage(audio_assets, pipeline_runs, jobs),
            self._publishing_stage(publish_jobs, jobs),
        ]

    def build_panel(self, episode: Episode) -> dict[str, Any]:
        stages = self.build_pipeline(episode)
        return {
            "stages": [self._stage_to_dict(stage) for stage in stages],
            "overview": self._build_overview(episode, stages),
        }

    def as_dicts(self, episode: Episode) -> list[dict[str, Any]]:
        return self.build_panel(episode)["stages"]

    def _build_overview(
        self, episode: Episode, stages: list[PipelineStage]
    ) -> dict[str, Any]:
        display_statuses = [stage.display_status for stage in stages]
        if any(status == "FAILED" for status in display_statuses):
            overall_status = "FAILED"
        elif all(status == "SUCCESS" for status in display_statuses):
            overall_status = "SUCCESS"
        elif any(status in {"RUNNING", "QUEUED"} for status in display_statuses):
            overall_status = "RUNNING"
        else:
            overall_status = "PENDING"

        completed = sum(1 for status in display_statuses if status == "SUCCESS")
        progress_percent = round((completed / len(stages)) * 100) if stages else 0
        if overall_status == "RUNNING" and progress_percent < 100:
            progress_percent = min(progress_percent + 5, 95)

        started_at = episode.created_at
        stage_starts = [stage.started_at for stage in stages if stage.started_at]
        if stage_starts:
            started_at = min(stage_starts)

        finished_at = None
        if overall_status == "SUCCESS":
            stage_finishes = [
                stage.finished_at for stage in stages if stage.finished_at
            ]
            if stage_finishes:
                finished_at = max(stage_finishes)

        articles = episode.articles.all()
        audio_ready = episode.audio_assets.filter(
            status=AudioAssetStatus.READY
        ).count()
        script_ready = episode.scripts.filter(
            status__in=["ready", "approved"]
        ).count()

        return {
            "run_id": str(episode.id)[:8],
            "overall_status": overall_status,
            "progress_percent": progress_percent,
            "started_at": started_at,
            "finished_at": finished_at,
            "metrics": [
                {"label": "Articles", "value": articles.count()},
                {"label": "Summarized", "value": self._summarized_count(list(articles))},
                {
                    "label": "Classified",
                    "value": self._classified_count(list(articles)),
                },
                {
                    "label": "Ranked",
                    "value": articles.filter(importance_score__isnull=False).count(),
                },
                {"label": "Audio ready", "value": audio_ready or script_ready},
            ],
        }

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
        return self._make_stage(
            name="News Collection",
            status=status,
            job=job,
            items_count=articles_count or None,
        )

    def _generic_job_stage(
        self,
        name: str,
        jobs: list[Job],
        job_type: str,
        *,
        items: int | None = None,
    ) -> PipelineStage:
        matching = [j for j in jobs if j.job_type == job_type]
        job = matching[-1] if matching else None
        return self._make_stage(
            name=name,
            status=job.status if job else "pending",
            job=job,
            items_count=items,
        )

    def _ranking_stage(
        self,
        episode: Episode,
        jobs: list[Job],
        articles: list,
    ) -> PipelineStage:
        planning = [j for j in jobs if j.job_type == "episode_planning"]
        job = planning[-1] if planning else None
        has_scores = any(article.importance_score is not None for article in articles)
        status = job.status if job else ("completed" if has_scores else "pending")
        ranked_count = sum(
            1 for article in articles if article.importance_score is not None
        )
        return self._make_stage(
            name="Ranking",
            status=status,
            job=job,
            items_count=ranked_count or None,
        )

    def _script_stage(self, script, jobs: list[Job]) -> PipelineStage:
        script_jobs = [j for j in jobs if j.job_type == "generate_script"]
        job = script_jobs[-1] if script_jobs else None
        status = script.status if script else (job.status if job else "pending")
        items = script.segments.count() if script else None
        return self._make_stage(
            name="Script",
            status=status,
            job=job,
            items_count=items,
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
        ready = sum(1 for asset in assets if asset.status == AudioAssetStatus.READY)
        run = pipeline_runs[-1] if pipeline_runs else None
        status = run.status if run else ("completed" if ready else "pending")
        if job:
            status = job.status
        return self._make_stage(
            name="Audio",
            status=status,
            job=job,
            items_count=ready or len(assets) or None,
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
        return self._make_stage(
            name="Publishing",
            status=status,
            job=job,
            started_at=started_at,
            finished_at=finished_at,
            error=error,
            items_count=len(publish_jobs) or None,
        )

    def _make_stage(
        self,
        *,
        name: str,
        status: str,
        job: Job | None,
        items_count: int | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        error: str = "",
    ) -> PipelineStage:
        duration_seconds = self._job_duration(job)
        return PipelineStage(
            name=name,
            status=status,
            display_status=self._display_status(status),
            duration_seconds=duration_seconds,
            duration_label=self._format_duration(duration_seconds),
            started_at=started_at if started_at is not None else (job.started_at if job else None),
            finished_at=finished_at
            if finished_at is not None
            else (job.completed_at if job else None),
            error=error or (job.error_message if job else ""),
            description=STAGE_DESCRIPTIONS[name],
            items_count=items_count,
        )

    @staticmethod
    def _summarized_count(articles: list) -> int:
        return sum(1 for article in articles if article.summary.strip())

    @staticmethod
    def _classified_count(articles: list) -> int:
        return sum(
            1
            for article in articles
            if article.classified_at is not None or article.category.strip()
        )

    @staticmethod
    def _display_status(status: str) -> str:
        normalized = (status or "pending").lower()
        if normalized in SUCCESS_STATUSES:
            return "SUCCESS"
        if normalized in FAILED_STATUSES:
            return "FAILED"
        if normalized in {JobStatus.QUEUED, "queued", JobStatus.PENDING, "pending"}:
            if normalized == JobStatus.QUEUED or normalized == "queued":
                return "QUEUED"
            return "PENDING"
        if normalized in RUNNING_STATUSES:
            return "RUNNING"
        return normalized.upper()

    @staticmethod
    def _format_duration(duration_seconds: float | None) -> str:
        if duration_seconds is None:
            return "0:00"
        total_seconds = max(0, int(duration_seconds))
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes}:{seconds:02d}"

    def _job_duration(self, job: Job | None) -> float | None:
        if job is None or not job.started_at or not job.completed_at:
            return None
        return (job.completed_at - job.started_at).total_seconds()

    @staticmethod
    def _stage_to_dict(stage: PipelineStage) -> dict[str, Any]:
        return {
            "name": stage.name,
            "status": stage.status,
            "display_status": stage.display_status,
            "duration_seconds": stage.duration_seconds,
            "duration_label": stage.duration_label,
            "started_at": stage.started_at,
            "finished_at": stage.finished_at,
            "error": stage.error,
            "description": stage.description,
            "items_count": stage.items_count,
        }
