"""Health check API views."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.mixins import RequestLoggingMixin
from api.v1.services.health import ApiHealthService


class HealthView(RequestLoggingMixin, APIView):
    """Overall platform health check."""

    resource_name = "health"

    @extend_schema(
        summary="Overall platform health",
        responses={200: OpenApiResponse(description="Health summary")},
    )
    def get(self, request: Request) -> Response:
        del request
        return Response(ApiHealthService().overall())


class CeleryHealthView(RequestLoggingMixin, APIView):
    """Celery infrastructure health check."""

    resource_name = "health-celery"

    @extend_schema(summary="Celery health check")
    def get(self, request: Request) -> Response:
        del request
        return Response(ApiHealthService().celery())


class LLMHealthView(RequestLoggingMixin, APIView):
    """LLM provider health check."""

    resource_name = "health-llm"

    @extend_schema(summary="LLM provider health check")
    def get(self, request: Request) -> Response:
        del request
        return Response(ApiHealthService().llm())


class TTSHealthView(RequestLoggingMixin, APIView):
    """TTS provider health check."""

    resource_name = "health-tts"

    @extend_schema(summary="TTS provider health check")
    def get(self, request: Request) -> Response:
        del request
        return Response(ApiHealthService().tts())


class PublishHealthView(RequestLoggingMixin, APIView):
    """Publishing platform health check."""

    resource_name = "health-publish"

    @extend_schema(summary="Publishing platform health check")
    def get(self, request: Request) -> Response:
        del request
        return Response(ApiHealthService().publish())
