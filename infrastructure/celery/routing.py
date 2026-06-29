"""Celery task routing configuration."""

from domain.jobs.queues import (
    QUEUE_AUDIO,
    QUEUE_INGESTION,
    QUEUE_LLM,
    QUEUE_MONITORING,
    QUEUE_PUBLISHING,
    QUEUE_TTS,
)

TASK_ROUTES = {
    "scheduler.tasks.import_news.*": {"queue": QUEUE_INGESTION},
    "scheduler.tasks.planning.*": {"queue": QUEUE_LLM},
    "scheduler.tasks.script.*": {"queue": QUEUE_LLM},
    "scheduler.tasks.summarize.*": {"queue": QUEUE_LLM},
    "scheduler.tasks.classify.*": {"queue": QUEUE_LLM},
    "scheduler.tasks.audio.*": {"queue": QUEUE_TTS},
    "scheduler.tasks.pipeline.*": {"queue": QUEUE_AUDIO},
    "scheduler.tasks.publish.*": {"queue": QUEUE_PUBLISHING},
    "scheduler.tasks.monitoring.*": {"queue": QUEUE_MONITORING},
}

TASK_ANNOTATIONS = {
    "scheduler.tasks.*": {
        "time_limit": None,
        "soft_time_limit": None,
    },
}
