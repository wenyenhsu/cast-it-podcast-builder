"""URL routes for the standalone operations dashboard."""

from django.urls import path

from apps.operations import views

app_name = "operations"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("providers/", views.provider_dashboard, name="providers"),
    path("health/", views.health_dashboard, name="health"),
    path("metrics/", views.metrics_dashboard, name="metrics"),
    path("logs/", views.logs_viewer, name="logs"),
    path(
        "pipeline/<uuid:episode_id>/",
        views.episode_pipeline,
        name="episode_pipeline",
    ),
]
