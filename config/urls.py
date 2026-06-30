"""URL configuration for the cast-it podcast builder project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("apps.operations.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]
