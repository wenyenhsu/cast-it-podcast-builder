"""Observability API views."""

from uuid import UUID

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.mixins import RequestLoggingMixin
from services.observability.dashboard import ObservabilityDashboardService
from services.observability.events import OperationalEventService
from services.observability.health.check_service import HealthCheckService
from services.observability.health.readiness import SystemReadinessService
from services.observability.metrics_service import ApplicationMetricsService
from services.observability.tracing_service import TracingService


class LiveHealthView(RequestLoggingMixin, APIView):
    """Liveness probe."""

    resource_name = "health-live"

    @extend_schema(summary="Liveness probe")
    def get(self, request: Request) -> Response:
        del request
        return Response(SystemReadinessService().liveness())


class ReadyHealthView(RequestLoggingMixin, APIView):
    """Readiness probe."""

    resource_name = "health-ready"

    @extend_schema(summary="Readiness probe")
    def get(self, request: Request) -> Response:
        del request
        return Response(SystemReadinessService().readiness())


class ComponentsHealthView(RequestLoggingMixin, APIView):
    """Detailed component health checks."""

    resource_name = "health-components"

    @extend_schema(summary="Component health checks")
    def get(self, request: Request) -> Response:
        del request
        return Response({"components": HealthCheckService().check_components()})


class MetricsView(RequestLoggingMixin, APIView):
    """Prometheus-style metrics export."""

    resource_name = "metrics"

    @extend_schema(summary="Metrics export")
    def get(self, request: Request) -> Response:
        metrics = ApplicationMetricsService()
        format_param = request.query_params.get("format", "json")
        if format_param == "prometheus":
            return Response(
                metrics.export_prometheus(),
                content_type="text/plain; version=0.0.4",
            )
        return Response(metrics.export())


class MetricsSummaryView(RequestLoggingMixin, APIView):
    """Metrics summary for dashboards."""

    resource_name = "metrics-summary"

    @extend_schema(summary="Metrics summary")
    def get(self, request: Request) -> Response:
        del request
        return Response(ApplicationMetricsService().summary())


class MetricsProvidersView(RequestLoggingMixin, APIView):
    """Provider-specific metrics."""

    resource_name = "metrics-providers"

    @extend_schema(summary="Provider metrics")
    def get(self, request: Request) -> Response:
        del request
        return Response(ApplicationMetricsService().providers_summary())


class MetricsJobsView(RequestLoggingMixin, APIView):
    """Job execution metrics."""

    resource_name = "metrics-jobs"

    @extend_schema(summary="Job metrics")
    def get(self, request: Request) -> Response:
        del request
        return Response(ApplicationMetricsService().jobs_summary())


class MetricsWorkflowsView(RequestLoggingMixin, APIView):
    """Workflow execution metrics."""

    resource_name = "metrics-workflows"

    @extend_schema(summary="Workflow metrics")
    def get(self, request: Request) -> Response:
        del request
        return Response(ApplicationMetricsService().workflows_summary())


class LogsListView(RequestLoggingMixin, APIView):
    """Operational event log listing."""

    resource_name = "logs"

    @extend_schema(summary="List operational events")
    def get(self, request: Request) -> Response:
        service = OperationalEventService()
        events = service.list_events(
            event_type=request.query_params.get("event_type", ""),
            severity=request.query_params.get("severity", ""),
            correlation_id=request.query_params.get("correlation_id", ""),
            job_id=request.query_params.get("job_id", ""),
            workflow_run_id=request.query_params.get("workflow_run_id", ""),
            episode_id=request.query_params.get("episode_id", ""),
            provider=request.query_params.get("provider", ""),
            search=request.query_params.get("search", ""),
            limit=int(request.query_params.get("limit", "100")),
        )
        return Response(
            [OperationalEventService.dto_to_dict(event) for event in events]
        )


class LogDetailView(RequestLoggingMixin, APIView):
    """Single operational event detail."""

    resource_name = "logs-detail"

    @extend_schema(
        summary="Get operational event",
        responses={200: OpenApiResponse(description="Event detail")},
    )
    def get(self, request: Request, event_id: str) -> Response:
        del request
        service = OperationalEventService()
        event = service.get(UUID(event_id))
        if event is None:
            return Response({"detail": "Event not found."}, status=404)
        return Response(OperationalEventService.dto_to_dict(event))


class TracesListView(RequestLoggingMixin, APIView):
    """Distributed trace span listing."""

    resource_name = "traces"

    @extend_schema(summary="List trace spans")
    def get(self, request: Request) -> Response:
        tracing = TracingService()
        spans = tracing.list_spans(
            trace_id=request.query_params.get("trace_id", ""),
            limit=int(request.query_params.get("limit", "100")),
        )
        return Response([tracing.span_to_dict(span) for span in spans])


class TraceDetailView(RequestLoggingMixin, APIView):
    """Single trace span detail."""

    resource_name = "traces-detail"

    @extend_schema(summary="Get trace span")
    def get(self, request: Request, span_id: str) -> Response:
        del request
        tracing = TracingService()
        span = tracing.get_span(span_id)
        if span is None:
            return Response({"detail": "Trace span not found."}, status=404)
        return Response(tracing.span_to_dict(span))


class DashboardSummaryView(RequestLoggingMixin, APIView):
    """Operational dashboard summary data."""

    resource_name = "observability-dashboard"

    @extend_schema(summary="Operational dashboard summary")
    def get(self, request: Request) -> Response:
        del request
        return Response(ObservabilityDashboardService().summary())
