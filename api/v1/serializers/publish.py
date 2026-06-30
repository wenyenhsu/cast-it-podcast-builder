"""Publish job serializers."""

from rest_framework import serializers

from apps.publish.models import PublishJob


class PublishJobListSerializer(serializers.ModelSerializer):
    """Compact publish job list representation."""

    episode_title = serializers.CharField(source="episode.title", read_only=True)

    class Meta:
        model = PublishJob
        fields = (
            "id",
            "episode",
            "episode_title",
            "platform",
            "status",
            "published_url",
            "external_id",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PublishJobDetailSerializer(serializers.ModelSerializer):
    """Full publish job representation."""

    episode_title = serializers.CharField(source="episode.title", read_only=True)

    class Meta:
        model = PublishJob
        fields = (
            "id",
            "episode",
            "episode_title",
            "platform",
            "status",
            "published_url",
            "external_id",
            "started_at",
            "completed_at",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
