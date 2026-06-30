"""API permission structure tests."""

from django.contrib.auth.models import User
from rest_framework.test import APIClient, APIRequestFactory

from api.v1.permissions import IsAdminOrReadOnly, IsAuthenticated, IsOwnerOrAdmin


def test_is_authenticated_denies_anonymous() -> None:
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = None  # type: ignore[assignment]
    permission = IsAuthenticated()
    assert permission.has_permission(request, object()) is False


def test_is_admin_or_read_only_allows_get() -> None:
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = User(is_staff=False)
    permission = IsAdminOrReadOnly()
    assert permission.has_permission(request, object()) is True


def test_is_admin_or_read_only_denies_post_for_non_admin() -> None:
    factory = APIRequestFactory()
    request = factory.post("/")
    request.user = User(is_staff=False)
    permission = IsAdminOrReadOnly()
    assert permission.has_permission(request, object()) is False


def test_is_owner_or_admin_allows_staff(api_client: APIClient, db: None) -> None:
    del api_client
    factory = APIRequestFactory()
    request = factory.patch("/")
    request.user = User(is_staff=True)
    permission = IsOwnerOrAdmin()
    assert permission.has_object_permission(request, object(), object()) is True
