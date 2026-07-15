"""Build Celery Beat schedule from environment configuration."""

import logging
import os

from celery.schedules import crontab
from django.conf import settings

from domain.jobs.exceptions import SchedulerConfigurationError

logger = logging.getLogger(__name__)

BEAT_TASK_PATHS = {
    "import_news": "scheduler.tasks.import_news.import_news_scheduled",
    "episode_planning": "scheduler.tasks.planning.episode_planning_scheduled",
    "generate_audio": "scheduler.tasks.audio.generate_audio_scheduled",
    "publish_episode": "scheduler.tasks.publish.publish_episode_scheduled",
    "publish_supabase": "scheduler.tasks.publish.publish_supabase_scheduled",
    "retry_failed_jobs": "scheduler.tasks.monitoring.retry_failed_jobs_scheduled",
    "provider_health_check": (
        "scheduler.tasks.monitoring.provider_health_check_scheduled"
    ),
}


def parse_cron_expression(expression: str) -> crontab:
    """Parse a five-field cron expression into a Celery crontab."""
    parts = expression.split()
    if len(parts) != 5:
        raise SchedulerConfigurationError(
            f"Invalid cron expression '{expression}'. Expected 5 fields."
        )
    minute, hour, day_of_month, month_of_year, day_of_week = parts
    return crontab(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        day_of_week=day_of_week,
    )


def _cron_from_env(env_key: str, default: str) -> crontab:
    value = os.environ.get(env_key) or getattr(settings, env_key, default)
    return parse_cron_expression(str(value))


def build_beat_schedule() -> dict[str, dict[str, object]]:
    """Build Celery Beat schedule from environment variables."""
    schedule = {
        "daily-news-import": {
            "task": BEAT_TASK_PATHS["import_news"],
            "schedule": _cron_from_env("BEAT_IMPORT_NEWS_CRON", "0 6 * * *"),
            "options": {"queue": "ingestion"},
        },
        "daily-episode-planning": {
            "task": BEAT_TASK_PATHS["episode_planning"],
            "schedule": _cron_from_env("BEAT_EPISODE_PLANNING_CRON", "0 7 * * *"),
            "options": {"queue": "llm"},
        },
        "daily-audio-generation": {
            "task": BEAT_TASK_PATHS["generate_audio"],
            "schedule": _cron_from_env("BEAT_GENERATE_AUDIO_CRON", "0 9 * * *"),
            "options": {"queue": "tts"},
        },
        "daily-publishing": {
            "task": BEAT_TASK_PATHS["publish_episode"],
            "schedule": _cron_from_env("BEAT_PUBLISH_EPISODE_CRON", "0 10 * * *"),
            "options": {"queue": "publishing"},
        },
        "daily-supabase-publish": {
            "task": BEAT_TASK_PATHS["publish_supabase"],
            "schedule": _cron_from_env("BEAT_PUBLISH_SUPABASE_CRON", "30 10 * * *"),
            "options": {"queue": "publishing"},
        },
        "failed-job-retry-sweep": {
            "task": BEAT_TASK_PATHS["retry_failed_jobs"],
            "schedule": _cron_from_env("BEAT_RETRY_SWEEP_CRON", "*/30 * * * *"),
            "options": {"queue": "monitoring"},
        },
        "provider-health-check": {
            "task": BEAT_TASK_PATHS["provider_health_check"],
            "schedule": _cron_from_env("BEAT_HEALTH_CHECK_CRON", "*/15 * * * *"),
            "options": {"queue": "monitoring"},
        },
    }
    logger.info(
        "Celery Beat schedule built",
        extra={
            "event": "beat_schedule_built",
            "schedule_keys": list(schedule.keys()),
        },
    )
    return schedule
