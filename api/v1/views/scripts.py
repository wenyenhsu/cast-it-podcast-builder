"""Script API views."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.request import Request
from rest_framework.response import Response

from api.v1.filters import ScriptFilter, ScriptSegmentFilter
from api.v1.mixins import RequestLoggingMixin
from api.v1.serializers.common import JobAcceptedSerializer
from api.v1.serializers.scripts import (
    ScriptDetailSerializer,
    ScriptListSerializer,
    ScriptSegmentDetailSerializer,
    ScriptSegmentListSerializer,
    ScriptSegmentWriteSerializer,
    ScriptValidationResultSerializer,
    ScriptWriteSerializer,
)
from api.v1.services.job_dispatch import ApiJobDispatchService
from api.v1.services.script_validation import validate_stored_script
from apps.scheduler.models import JobType
from apps.scripts.models import Script, ScriptSegment


class ScriptViewSet(RequestLoggingMixin, viewsets.ModelViewSet):
    """CRUD API for podcast scripts."""

    resource_name = "script"
    queryset = Script.objects.select_related("episode")
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ScriptFilter
    search_fields = ["title", "episode__title"]
    ordering_fields = ["created_at", "updated_at", "generated_at", "version"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ScriptListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return ScriptWriteSerializer
        return ScriptDetailSerializer

    @extend_schema(responses={202: JobAcceptedSerializer})
    @action(detail=True, methods=["post"])
    def regenerate(self, request: Request, pk: str | None = None) -> Response:
        del request
        script = self.get_object()
        job = ApiJobDispatchService().dispatch(
            JobType.GENERATE_SCRIPT,
            {"episode_id": str(script.episode_id), "script_id": str(script.id)},
        )
        self.log_action(
            action="regenerate", resource_id=str(script.id), job_id=str(job.id)
        )
        return Response(
            ApiJobDispatchService().build_accepted_response(
                job,
                detail="Script regeneration has been queued.",
            ),
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={200: ScriptValidationResultSerializer})
    @action(detail=True, methods=["post"])
    def validate(self, request: Request, pk: str | None = None) -> Response:
        del request
        script = self.get_object()
        result = validate_stored_script(script)
        self.log_action(action="validate", resource_id=str(script.id))
        return Response(
            ScriptValidationResultSerializer(
                {
                    "passed": result.passed,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "estimated_duration_seconds": result.estimated_duration_seconds,
                    "segment_count": result.segment_count,
                }
            ).data
        )


class ScriptSegmentViewSet(RequestLoggingMixin, viewsets.ModelViewSet):
    """CRUD API for script segments."""

    resource_name = "script-segment"
    queryset = ScriptSegment.objects.select_related("script")
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ScriptSegmentFilter
    ordering_fields = ["sequence", "created_at"]
    ordering = ["script", "sequence"]

    def get_serializer_class(self):
        if self.action == "list":
            return ScriptSegmentListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return ScriptSegmentWriteSerializer
        return ScriptSegmentDetailSerializer
