"""Release and build metadata API view."""

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.mixins import RequestLoggingMixin
from infrastructure.deployment.version import get_build_metadata


class VersionView(RequestLoggingMixin, APIView):
    """Expose traceable build and release metadata."""

    resource_name = "version"

    @extend_schema(summary="Application version and build metadata")
    def get(self, request: Request) -> Response:
        del request
        return Response(get_build_metadata().as_dict())
