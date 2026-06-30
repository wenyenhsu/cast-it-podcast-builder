"""Episode API views."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.request import Request
from rest_framework.response import Response

from api.v1.filters import EpisodeFilter
from api.v1.mixins import RequestLoggingMixin
from api.v1.serializers.common import JobAcceptedSerializer
from api.v1.serializers.episodes import (
    EpisodeDetailSerializer,
    EpisodeListSerializer,
    EpisodePublishSerializer,
    EpisodeWriteSerializer,
)
from api.v1.services.job_dispatch import ApiJobDispatchService
from apps.episodes.models import Episode
from apps.scheduler.models import JobType


class EpisodeViewSet(RequestLoggingMixin, viewsets.ModelViewSet):
    """CRUD API for podcast episodes."""

    resource_name = "episode"
    queryset = Episode.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EpisodeFilter
    search_fields = ["title", "description", "summary"]
    ordering_fields = ["created_at", "updated_at", "publish_date", "duration_seconds"]
    ordering = ["-publish_date", "-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return EpisodeListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return EpisodeWriteSerializer
        return EpisodeDetailSerializer

    @extend_schema(responses={202: JobAcceptedSerializer})
    @action(detail=True, methods=["post"])
    def plan(self, request: Request, pk: str | None = None) -> Response:
        del request
        episode = self.get_object()
        job = ApiJobDispatchService().dispatch(
            JobType.EPISODE_PLANNING,
            {"episode_id": str(episode.id)},
        )
        self.log_action(action="plan", resource_id=str(episode.id), job_id=str(job.id))
        return Response(
            ApiJobDispatchService().build_accepted_response(job),
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={202: JobAcceptedSerializer})
    @action(detail=True, methods=["post"], url_path="generate-script")
    def generate_script(self, request: Request, pk: str | None = None) -> Response:
        del request
        episode = self.get_object()
        job = ApiJobDispatchService().dispatch(
            JobType.GENERATE_SCRIPT,
            {"episode_id": str(episode.id)},
        )
        self.log_action(
            action="generate_script",
            resource_id=str(episode.id),
            job_id=str(job.id),
        )
        return Response(
            ApiJobDispatchService().build_accepted_response(job),
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={202: JobAcceptedSerializer})
    @action(detail=True, methods=["post"], url_path="generate-audio")
    def generate_audio(self, request: Request, pk: str | None = None) -> Response:
        del request
        episode = self.get_object()
        job = ApiJobDispatchService().dispatch(
            JobType.GENERATE_AUDIO,
            {"episode_id": str(episode.id)},
        )
        self.log_action(
            action="generate_audio",
            resource_id=str(episode.id),
            job_id=str(job.id),
        )
        return Response(
            ApiJobDispatchService().build_accepted_response(job),
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        request=EpisodePublishSerializer,
        responses={202: JobAcceptedSerializer},
    )
    @action(detail=True, methods=["post"])
    def publish(self, request: Request, pk: str | None = None) -> Response:
        episode = self.get_object()
        serializer = EpisodePublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload: dict[str, object] = {"episode_id": str(episode.id)}
        platforms = serializer.validated_data.get("platforms")
        if platforms:
            payload["platforms"] = platforms
        job = ApiJobDispatchService().dispatch(JobType.PUBLISH_EPISODE, payload)
        self.log_action(
            action="publish", resource_id=str(episode.id), job_id=str(job.id)
        )
        return Response(
            ApiJobDispatchService().build_accepted_response(job),
            status=status.HTTP_202_ACCEPTED,
        )
