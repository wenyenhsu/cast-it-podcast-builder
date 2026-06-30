"""Shared API serializers."""

from rest_framework import serializers

from apps.scheduler.models import Job


class JobAcceptedSerializer(serializers.Serializer):
    """Standard async job acceptance response."""

    job_id = serializers.UUIDField()
    status = serializers.CharField()
    detail = serializers.CharField()
    status_url = serializers.CharField()


class JobSerializer(serializers.ModelSerializer):
    """Background job representation."""

    class Meta:
        model = Job
        fields = (
            "id",
            "job_type",
            "status",
            "progress",
            "payload",
            "result",
            "error_message",
            "started_at",
            "completed_at",
            "retry_count",
            "celery_task_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class JobListSerializer(serializers.ModelSerializer):
    """Compact job list representation."""

    class Meta:
        model = Job
        fields = (
            "id",
            "job_type",
            "status",
            "progress",
            "retry_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
