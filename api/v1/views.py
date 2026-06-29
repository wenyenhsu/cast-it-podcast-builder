"""API v1 views."""

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
def health_check(request: Request) -> Response:
    """Placeholder health check endpoint for API readiness verification."""
    return Response({"status": "ok"})
