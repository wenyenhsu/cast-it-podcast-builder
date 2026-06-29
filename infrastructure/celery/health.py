"""Celery and Redis health checks."""

import logging
from typing import Any, Protocol, cast

from django.core.cache import cache

from domain.jobs.exceptions import SchedulerConfigurationError

logger = logging.getLogger(__name__)

EXPECTED_TASKS = {
    "scheduler.tasks.import_news.import_news_task",
    "scheduler.tasks.planning.episode_planning_task",
    "scheduler.tasks.script.generate_script_task",
    "scheduler.tasks.audio.generate_audio_task",
    "scheduler.tasks.pipeline.run_audio_pipeline_task",
    "scheduler.tasks.publish.publish_episode_task",
    "scheduler.tasks.monitoring.retry_failed_jobs_task",
    "scheduler.tasks.monitoring.provider_health_check_task",
    "scheduler.tasks.summarize.summarize_article_task",
    "scheduler.tasks.classify.classify_article_task",
}


class CeleryInspectClient(Protocol):
    """Protocol for Celery control inspect API."""

    def registered(self) -> dict[str, list[str]] | None: ...

    def ping(self) -> dict[str, dict[str, str]] | None: ...


class CeleryHealthService:
    """Health checks for Celery infrastructure."""

    def __init__(self, inspect_client: CeleryInspectClient | None = None) -> None:
        self._inspect = inspect_client

    def check_redis(self) -> bool:
        """Verify Redis cache/broker connectivity."""
        try:
            cache.set("celery_health_check", "ok", timeout=5)
            return bool(cache.get("celery_health_check") == "ok")
        except Exception:
            logger.warning(
                "Redis health check failed",
                extra={"event": "redis_health_check_failed"},
            )
            return False

    def check_workers(self) -> bool:
        """Verify at least one Celery worker responds to ping."""
        inspect = self._get_inspect()
        if inspect is None:
            return False
        try:
            response = inspect.ping()
            return bool(response)
        except Exception:
            logger.warning(
                "Celery worker health check failed",
                extra={"event": "celery_worker_health_check_failed"},
            )
            return False

    def check_task_registration(self) -> bool:
        """Verify expected tasks are registered on workers."""
        inspect = self._get_inspect()
        if inspect is None:
            return False
        try:
            registered = inspect.registered() or {}
            all_tasks = set()
            for tasks in registered.values():
                all_tasks.update(tasks)
            missing = EXPECTED_TASKS - all_tasks
            if missing:
                logger.warning(
                    "Missing registered Celery tasks",
                    extra={
                        "event": "celery_tasks_missing",
                        "missing_tasks": sorted(missing),
                    },
                )
                return False
            return True
        except Exception:
            logger.warning(
                "Celery task registration check failed",
                extra={"event": "celery_task_registration_failed"},
            )
            return False

    def check_all(self) -> dict[str, Any]:
        """Run all health checks and return a summary."""
        results = {
            "redis": self.check_redis(),
            "workers": self.check_workers(),
            "task_registration": self.check_task_registration(),
        }
        results["healthy"] = all(results.values())
        logger.info(
            "Celery health check completed",
            extra={"event": "celery_health_check_completed", **results},
        )
        return results

    def _get_inspect(self) -> CeleryInspectClient | None:
        if self._inspect is not None:
            return self._inspect
        try:
            from config.celery import app

            client = app.control.inspect(timeout=1.0)
            return cast(CeleryInspectClient | None, client)
        except Exception as exc:
            raise SchedulerConfigurationError(
                f"Failed to initialize Celery inspect client: {exc}"
            ) from exc
