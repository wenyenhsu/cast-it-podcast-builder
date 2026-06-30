"""News source API views."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.request import Request
from rest_framework.response import Response

from api.v1.filters import NewsSourceFilter, ProviderHealthCheckFilter
from api.v1.mixins import RequestLoggingMixin
from api.v1.serializers.common import JobAcceptedSerializer
from api.v1.serializers.providers import (
    NewsSourceDetailSerializer,
    NewsSourceListSerializer,
    NewsSourceWriteSerializer,
    ProviderHealthCheckSerializer,
)
from api.v1.services.job_dispatch import ApiJobDispatchService
from apps.providers.models import NewsSource, ProviderHealthCheck
from apps.scheduler.models import JobType


class NewsSourceViewSet(RequestLoggingMixin, viewsets.ModelViewSet):
    """CRUD API for news sources."""

    resource_name = "news-source"
    queryset = NewsSource.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = NewsSourceFilter
    search_fields = ["name", "rss_url", "homepage"]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return NewsSourceListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return NewsSourceWriteSerializer
        return NewsSourceDetailSerializer

    @extend_schema(responses={202: JobAcceptedSerializer})
    @action(detail=True, methods=["post"], url_path="health-check")
    def health_check(self, request: Request, pk: str | None = None) -> Response:
        del request
        source = self.get_object()
        job = ApiJobDispatchService().dispatch(
            JobType.HEALTH_CHECK,
            {"source_id": str(source.id), "provider_type": source.provider_type},
        )
        self.log_action(
            action="health_check", resource_id=str(source.id), job_id=str(job.id)
        )
        return Response(
            ApiJobDispatchService().build_accepted_response(
                job,
                detail="Provider health check has been queued.",
            ),
            status=status.HTTP_202_ACCEPTED,
        )


class ProviderHealthCheckViewSet(RequestLoggingMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only API for provider health check records."""

    resource_name = "provider-health-check"
    queryset = ProviderHealthCheck.objects.select_related("news_source")
    serializer_class = ProviderHealthCheckSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ProviderHealthCheckFilter
    ordering_fields = ["checked_at", "created_at"]
    ordering = ["-checked_at"]
