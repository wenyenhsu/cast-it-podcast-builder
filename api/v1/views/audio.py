"""Audio asset and voice API views."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.request import Request
from rest_framework.response import Response

from api.v1.filters import (
    AudioAssetFilter,
    PersonaVoiceMappingFilter,
    PipelineRunFilter,
    VoiceProfileFilter,
)
from api.v1.mixins import RequestLoggingMixin
from api.v1.serializers.audio import (
    AudioAssetDetailSerializer,
    AudioAssetListSerializer,
    PersonaVoiceMappingSerializer,
    PipelineRunSerializer,
    VoiceProfileSerializer,
)
from api.v1.serializers.common import JobAcceptedSerializer
from api.v1.services.job_dispatch import ApiJobDispatchService
from apps.audio.models import AudioAsset, PersonaVoiceMapping, PipelineRun, VoiceProfile
from apps.scheduler.models import JobType


class AudioAssetViewSet(RequestLoggingMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only API for audio assets with async regeneration and pipeline."""

    resource_name = "audio-asset"
    queryset = AudioAsset.objects.select_related("episode", "script_segment")
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = AudioAssetFilter
    search_fields = ["episode__title", "provider", "voice"]
    ordering_fields = ["created_at", "updated_at", "duration", "generated_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return AudioAssetListSerializer
        return AudioAssetDetailSerializer

    @extend_schema(responses={202: JobAcceptedSerializer})
    @action(detail=True, methods=["post"])
    def regenerate(self, request: Request, pk: str | None = None) -> Response:
        del request
        asset = self.get_object()
        job = ApiJobDispatchService().dispatch(
            JobType.GENERATE_AUDIO,
            {
                "episode_id": str(asset.episode_id),
                "audio_asset_id": str(asset.id),
            },
        )
        self.log_action(
            action="regenerate", resource_id=str(asset.id), job_id=str(job.id)
        )
        return Response(
            ApiJobDispatchService().build_accepted_response(
                job,
                detail="Audio regeneration has been queued.",
            ),
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={202: JobAcceptedSerializer})
    @action(detail=True, methods=["post"])
    def pipeline(self, request: Request, pk: str | None = None) -> Response:
        del request
        asset = self.get_object()
        job = ApiJobDispatchService().dispatch(
            JobType.RUN_AUDIO_PIPELINE,
            {
                "episode_id": str(asset.episode_id),
                "audio_asset_id": str(asset.id),
            },
        )
        self.log_action(
            action="pipeline", resource_id=str(asset.id), job_id=str(job.id)
        )
        return Response(
            ApiJobDispatchService().build_accepted_response(job),
            status=status.HTTP_202_ACCEPTED,
        )


class VoiceProfileViewSet(RequestLoggingMixin, viewsets.ModelViewSet):
    """CRUD API for voice profiles."""

    resource_name = "voice-profile"
    queryset = VoiceProfile.objects.all()
    serializer_class = VoiceProfileSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = VoiceProfileFilter
    search_fields = ["name", "provider", "description"]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["provider", "name"]


class PersonaVoiceMappingViewSet(RequestLoggingMixin, viewsets.ModelViewSet):
    """CRUD API for persona voice mappings."""

    resource_name = "persona-voice-mapping"
    queryset = PersonaVoiceMapping.objects.select_related("voice_profile")
    serializer_class = PersonaVoiceMappingSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PersonaVoiceMappingFilter
    ordering_fields = ["persona", "created_at"]
    ordering = ["provider", "persona"]


class PipelineRunViewSet(RequestLoggingMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only API for audio pipeline runs."""

    resource_name = "pipeline-run"
    queryset = PipelineRun.objects.select_related("episode", "audio_asset")
    serializer_class = PipelineRunSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PipelineRunFilter
    ordering_fields = ["created_at", "started_at", "completed_at"]
    ordering = ["-created_at"]
