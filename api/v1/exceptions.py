"""API exception handling."""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ConflictError(APIException):
    """Raised when a resource conflicts with existing data."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource conflict."
    default_code = "conflict"


class ServiceUnavailableError(APIException):
    """Raised when a required backend service is unavailable."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service unavailable."
    default_code = "service_unavailable"


def _format_validation_errors(detail: Any) -> dict[str, list[str]]:
    if isinstance(detail, dict):
        formatted: dict[str, list[str]] = {}
        for key, value in detail.items():
            if isinstance(value, (list, tuple)):
                formatted[str(key)] = [str(item) for item in value]
            else:
                formatted[str(key)] = [str(value)]
        return formatted
    if isinstance(detail, list):
        return {"non_field_errors": [str(item) for item in detail]}
    return {"non_field_errors": [str(detail)]}


def api_exception_handler(
    exc: Exception,
    context: dict[str, Any],
) -> Response | None:
    """Return standardized API error responses."""
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            errors = _format_validation_errors(exc.message_dict)
        elif hasattr(exc, "messages"):
            errors = _format_validation_errors(exc.messages)
        else:
            errors = {"non_field_errors": [str(exc)]}
        return Response(
            {"detail": "Validation failed", "errors": errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        response.data = {
            "detail": "Validation failed",
            "errors": _format_validation_errors(exc.detail),
        }
        return response

    if isinstance(exc, Http404):
        response.data = {"detail": "Resource not found."}
        return response

    if isinstance(exc, APIException):
        detail = exc.detail
        if isinstance(detail, (list, dict)):
            response.data = {
                "detail": "Request failed",
                "errors": _format_validation_errors(detail),
            }
        else:
            response.data = {"detail": str(detail)}
        return response

    return response
