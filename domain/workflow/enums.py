"""Workflow domain enums."""

from django.db import models


class WorkflowStatus(models.TextChoices):
    """Status values for workflow and step runs."""

    PENDING = "pending", "Pending"
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    PAUSED = "paused", "Paused"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"
    RETRYING = "retrying", "Retrying"
    SKIPPED = "skipped", "Skipped"


class WorkflowStepType(models.TextChoices):
    """Logical workflow step types mapped to business adapters."""

    INDEX_KNOWLEDGE = "index_knowledge", "Index Knowledge"
    COLLECT_ARTICLES = "collect_articles", "Collect Articles"
    SUMMARIZE_ARTICLES = "summarize_articles", "Summarize Articles"
    CLASSIFY_ARTICLES = "classify_articles", "Classify Articles"
    RANK_ARTICLES = "rank_articles", "Rank Articles"
    PLAN_EPISODE = "plan_episode", "Plan Episode"
    GENERATE_SCRIPT = "generate_script", "Generate Script"
    GENERATE_AUDIO = "generate_audio", "Generate Audio"
    PROCESS_AUDIO = "process_audio", "Process Audio"
    PUBLISH_EPISODE = "publish_episode", "Publish Episode"
