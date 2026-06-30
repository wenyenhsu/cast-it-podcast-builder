"""Observability persistence models."""

import uuid

from django.db import models


class OperationalEvent(models.Model):
    """Normalized operational event for visibility and troubleshooting."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100, db_index=True)
    severity = models.CharField(max_length=20, db_index=True)
    source = models.CharField(max_length=100)
    name = models.CharField(max_length=200, db_index=True)
    message = models.TextField()
    correlation_id = models.CharField(max_length=64, blank=True, db_index=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    job_id = models.CharField(max_length=64, blank=True, db_index=True)
    workflow_run_id = models.CharField(max_length=64, blank=True, db_index=True)
    episode_id = models.CharField(max_length=64, blank=True, db_index=True)
    provider = models.CharField(max_length=100, blank=True, db_index=True)
    duration_ms = models.FloatField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["severity", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.name}"
