"""Script serializers."""

from rest_framework import serializers

from apps.scripts.models import Script, ScriptSegment


class ScriptSegmentListSerializer(serializers.ModelSerializer):
    """Compact script segment representation."""

    class Meta:
        model = ScriptSegment
        fields = (
            "id",
            "script",
            "sequence",
            "speaker",
            "voice",
            "emotion",
            "estimated_duration_seconds",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ScriptSegmentDetailSerializer(serializers.ModelSerializer):
    """Full script segment representation."""

    class Meta:
        model = ScriptSegment
        fields = (
            "id",
            "script",
            "sequence",
            "speaker",
            "voice",
            "emotion",
            "text",
            "pause_before_seconds",
            "pause_after_seconds",
            "estimated_duration_seconds",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ScriptSegmentWriteSerializer(serializers.ModelSerializer):
    """Script segment create and update payload."""

    class Meta:
        model = ScriptSegment
        fields = (
            "script",
            "sequence",
            "speaker",
            "voice",
            "emotion",
            "text",
            "pause_before_seconds",
            "pause_after_seconds",
            "estimated_duration_seconds",
        )


class ScriptListSerializer(serializers.ModelSerializer):
    """Compact script list representation."""

    episode_title = serializers.CharField(source="episode.title", read_only=True)

    class Meta:
        model = Script
        fields = (
            "id",
            "episode",
            "episode_title",
            "version",
            "title",
            "status",
            "validation_status",
            "estimated_duration_seconds",
            "generated_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ScriptDetailSerializer(serializers.ModelSerializer):
    """Full script representation."""

    episode_title = serializers.CharField(source="episode.title", read_only=True)

    class Meta:
        model = Script
        fields = (
            "id",
            "episode",
            "episode_title",
            "version",
            "title",
            "llm_provider",
            "model_name",
            "prompt_version",
            "status",
            "validation_status",
            "estimated_duration_seconds",
            "generated_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ScriptWriteSerializer(serializers.ModelSerializer):
    """Script create and update payload."""

    class Meta:
        model = Script
        fields = (
            "episode",
            "version",
            "title",
            "llm_provider",
            "model_name",
            "prompt_version",
            "status",
            "validation_status",
            "estimated_duration_seconds",
        )


class ScriptValidationResultSerializer(serializers.Serializer):
    """Script validation action response."""

    passed = serializers.BooleanField()
    errors = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField())
    estimated_duration_seconds = serializers.IntegerField()
    segment_count = serializers.IntegerField()
