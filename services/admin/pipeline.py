"""Episode pipeline stage inspection for admin views."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from apps.episodes.models import Episode
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
    )

    def build_pipeline(self, episode: Episode) -> list[PipelineStage]:
        """Return ordered pipeline stages for an episode."""
        articles = list(episode.articles.all())
        article_ids = [str(article.id) for article in articles]
        episode_jobs = list(
            Job.objects.filter(payload__episode_id=str(episode.id)).order_by(
                "created_at"
            )
        )
        article_jobs = (
            list(
                Job.objects.filter(payload__article_id__in=article_ids).order_by(
                    "created_at"
                )
            )
            if article_ids
            else []
        )
        jobs = episode_jobs + [
            job
            for job in article_jobs
            if job.id not in {item.id for item in episode_jobs}
        ]
        latest_script = episode.scripts.order_by("-version").first()
        return [
            self._news_collection_stage(episode, articles, jobs),
            self._article_processing_stage(
                "Summary",
                jobs,
                "summarize_article",
                items=self._summarized_count(articles),
                domain_complete=self._summarized_count(articles) > 0,
            ),
            self._article_processing_stage(
                "Classification",
                jobs,
                "classify_article",
                items=self._classified_count(articles),
                domain_complete=self._classified_count(articles) > 0,
                started_at=self._earliest(
                    [
                        article.classified_at
                        for article in articles
                        if article.classified_at is not None
                    ]
                ),
                finished_at=self._latest(
                    [
                        article.classified_at
                        for article in articles
                        if article.classified_at is not None
                    ]
                ),
            ),
            self._ranking_stage(episode, jobs, articles),
            self._script_stage(latest_script, jobs),
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
        return {
            "run_id": str(episode.id)[:8],
            "overall_status": overall_status,
            "progress_percent": progress_percent,
            "started_at": started_at,
            "finished_at": finished_at,
            "metrics": [
                {"label": "Articles", "value": articles.count()},
                {
                    "label": "Summarized",
                    "value": self._summarized_count(list(articles)),
                },
                {
                    "label": "Classified",
                    "value": self._classified_count(list(articles)),
                },
                {
                    "label": "Ranked",
                    "value": articles.filter(importance_score__isnull=False).count(),
                },
            ],
        }

    def _news_collection_stage(
        self,
        episode: Episode,
        articles: list,
        jobs: list[Job],
    ) -> PipelineStage:
        articles_count = len(articles)
        import_jobs = [j for j in jobs if j.job_type == "import_news"]
        job = import_jobs[-1] if import_jobs else None
        status = "completed" if articles_count else "pending"
        if job:
            status = job.status
        job_started, job_finished = self._span_from_jobs(import_jobs)
        return self._make_stage(
            name="News Collection",
            status=status,
            job=job,
            items_count=articles_count or None,
            started_at=job_started,
            finished_at=job_finished,
        )

    def _article_processing_stage(
        self,
        name: str,
        jobs: list[Job],
        job_type: str,
        *,
        items: int | None = None,
        domain_complete: bool = False,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> PipelineStage:
        matching = [j for j in jobs if j.job_type == job_type]
        job = matching[-1] if matching else None
        active = any(
            self._display_status(item.status) in {"RUNNING", "QUEUED"}
            for item in matching
        )
        if active:
            status = next(
                item.status
                for item in reversed(matching)
                if self._display_status(item.status) in {"RUNNING", "QUEUED"}
            )
        elif job is not None:
            status = job.status
        elif domain_complete:
            status = "completed"
        else:
            status = "pending"
        job_started, job_finished = self._span_from_jobs(matching)
        return self._make_stage(
            name=name,
            status=status,
            job=job,
            items_count=items,
            started_at=started_at or job_started,
            finished_at=finished_at or job_finished,
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
        job_started, job_finished = self._span_from_jobs(planning)
        return self._make_stage(
            name="Ranking",
            status=status,
            job=job,
            items_count=ranked_count or None,
            started_at=job_started,
            finished_at=job_finished,
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
        resolved_started = (
            started_at if started_at is not None else (job.started_at if job else None)
        )
        resolved_finished = (
            finished_at
            if finished_at is not None
            else (job.completed_at if job else None)
        )
        duration_seconds = self._duration_seconds(
            resolved_started, resolved_finished, job=job
        )
        return PipelineStage(
            name=name,
            status=status,
            display_status=self._display_status(status),
            duration_seconds=duration_seconds,
            duration_label=self._format_duration(duration_seconds),
            started_at=resolved_started,
            finished_at=resolved_finished,
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
            return "—"
        total_seconds = max(0, int(round(duration_seconds)))
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes}:{seconds:02d}"

    def _duration_seconds(
        self,
        started_at: datetime | None,
        finished_at: datetime | None,
        *,
        job: Job | None = None,
    ) -> float | None:
        if started_at is not None and finished_at is not None:
            seconds = (finished_at - started_at).total_seconds()
            if seconds > 0:
                return seconds
        return self._job_duration(job)

    def _job_duration(self, job: Job | None) -> float | None:
        if job is None or not job.started_at or not job.completed_at:
            return None
        return (job.completed_at - job.started_at).total_seconds()

    @staticmethod
    def _earliest(values: list[datetime | None]) -> datetime | None:
        present = [value for value in values if value is not None]
        return min(present) if present else None

    @staticmethod
    def _latest(values: list[datetime | None]) -> datetime | None:
        present = [value for value in values if value is not None]
        return max(present) if present else None

    @staticmethod
    def _span_from_jobs(jobs: list[Job]) -> tuple[datetime | None, datetime | None]:
        started = [job.started_at for job in jobs if job.started_at]
        finished = [job.completed_at for job in jobs if job.completed_at]
        return (
            min(started) if started else None,
            max(finished) if finished else None,
        )

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
