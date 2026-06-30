"""URL routes for the standalone operations dashboard."""

from django.urls import path

from apps.operations import views

app_name = "operations"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("dashboard/insights/", views.dashboard_insights, name="dashboard_insights"),
    path("content/", views.content, name="content"),
    path("providers/", views.providers, name="providers"),
    path("providers/llm/", views.llm_provider_dashboard, name="llm"),
    path("providers/tts/", views.tts_provider_dashboard, name="tts"),
    path("monitor/", views.monitor, name="monitor"),
    path("health/", views.health_dashboard, name="health"),
    path("metrics/", views.metrics_dashboard, name="metrics"),
    path("logs/", views.logs_viewer, name="logs"),
    path(
        "scripts/",
        views.scripts,
        name="scripts",
    ),
    path(
        "scripts/<uuid:script_id>/",
        views.script_detail,
        name="script_detail",
    ),
    path(
        "api/jobs/<uuid:job_id>/",
        views.job_status_api,
        name="job_status_api",
    ),
    path(
        "tts/",
        views.tts_generation,
        name="tts_generation",
    ),
    path(
        "audio/<uuid:asset_id>/",
        views.audio_asset,
        name="audio_asset",
    ),
    path(
        "articles/<uuid:article_id>/",
        views.article_detail,
        name="article_detail",
    ),
    path(
        "pipeline/<uuid:episode_id>/",
        views.episode_pipeline,
        name="episode_pipeline",
    ),
]
