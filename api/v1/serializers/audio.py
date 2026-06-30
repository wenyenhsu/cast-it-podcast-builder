"""Audio asset and pipeline serializers."""

from rest_framework import serializers

from apps.audio.models import AudioAsset, PersonaVoiceMapping, PipelineRun, VoiceProfile


class AudioAssetListSerializer(serializers.ModelSerializer):
    """Compact audio asset list representation."""

    episode_title = serializers.CharField(source="episode.title", read_only=True)

    class Meta:
        model = AudioAsset
        fields = (
            "id",
            "episode",
            "episode_title",
            "script_segment",
            "provider",
            "voice",
            "duration",
            "format",
            "is_final_episode_audio",
            "status",
            "generated_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class AudioAssetDetailSerializer(serializers.ModelSerializer):
    """Full audio asset representation."""

    episode_title = serializers.CharField(source="episode.title", read_only=True)

    class Meta:
        model = AudioAsset
        fields = (
            "id",
            "episode",
            "episode_title",
            "script_segment",
            "provider",
            "voice",
            "file_path",
            "duration",
            "sample_rate",
            "bitrate",
            "format",
            "generation_time",
            "generated_at",
            "file_size",
            "checksum",
            "is_final_episode_audio",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class VoiceProfileSerializer(serializers.ModelSerializer):
    """Voice profile representation."""

    class Meta:
        model = VoiceProfile
        fields = (
            "id",
            "name",
            "provider",
            "provider_voice_id",
            "language",
            "gender",
            "description",
            "default_speed",
            "enabled",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class PersonaVoiceMappingSerializer(serializers.ModelSerializer):
    """Persona to voice mapping representation."""

    voice_profile_name = serializers.CharField(
        source="voice_profile.name",
        read_only=True,
    )

    class Meta:
        model = PersonaVoiceMapping
        fields = (
            "id",
            "persona",
            "voice_profile",
            "voice_profile_name",
            "provider",
            "enabled",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class PipelineRunSerializer(serializers.ModelSerializer):
    """Audio pipeline run representation."""

    episode_title = serializers.CharField(source="episode.title", read_only=True)

    class Meta:
        model = PipelineRun
        fields = (
            "id",
            "episode",
            "episode_title",
            "audio_asset",
            "status",
            "started_at",
            "completed_at",
            "output_path",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
