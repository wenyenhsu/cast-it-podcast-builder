"""API permission classes."""

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsAuthenticated(BasePermission):
    """Allow access only to authenticated users."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and request.user.is_authenticated)


class IsAdminOrReadOnly(BasePermission):
    """Allow read access to anyone; write access to admin users."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class IsOwnerOrAdmin(BasePermission):
    """Allow owners or admin users to modify a resource."""

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> bool:
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        owner = getattr(obj, "owner", None) or getattr(obj, "user", None)
        if owner is None:
            return user.is_staff
        return owner == user
