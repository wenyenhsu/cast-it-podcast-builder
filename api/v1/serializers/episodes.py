"""Episode serializers."""

from rest_framework import serializers

from apps.episodes.models import Episode


class EpisodeListSerializer(serializers.ModelSerializer):
    """Compact episode list representation."""

    class Meta:
        model = Episode
        fields = (
            "id",
            "title",
            "language",
            "publish_date",
            "status",
            "duration_seconds",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class EpisodeDetailSerializer(serializers.ModelSerializer):
    """Full episode representation."""

    class Meta:
        model = Episode
        fields = (
            "id",
            "title",
            "description",
            "summary",
            "language",
            "publish_date",
            "status",
            "duration_seconds",
            "cover_image",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class EpisodeWriteSerializer(serializers.ModelSerializer):
    """Episode create and update payload."""

    class Meta:
        model = Episode
        fields = (
            "title",
            "description",
            "summary",
            "language",
            "publish_date",
            "status",
            "duration_seconds",
            "cover_image",
        )


class EpisodePublishSerializer(serializers.Serializer):
    """Optional publish action payload."""

    platforms = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
