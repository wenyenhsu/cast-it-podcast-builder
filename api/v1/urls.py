"""API v1 URL configuration."""

from django.urls import path

from api.v1 import views

urlpatterns = [
    path("health/", views.health_check, name="health-check"),
]
