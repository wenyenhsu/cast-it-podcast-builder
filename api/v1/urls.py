"""API v1 URL routing."""

from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from api.v1.views.articles import ArticleViewSet, TagViewSet
from api.v1.views.audio import (
    AudioAssetViewSet,
    PersonaVoiceMappingViewSet,
    PipelineRunViewSet,
    VoiceProfileViewSet,
)
from api.v1.views.episodes import EpisodeViewSet
from api.v1.views.health import (
    CeleryHealthView,
    HealthView,
    LLMHealthView,
    PublishHealthView,
    TTSHealthView,
)
from api.v1.views.observability import (
    ComponentsHealthView,
    DashboardSummaryView,
    LiveHealthView,
    LogDetailView,
    LogsListView,
    MetricsJobsView,
    MetricsProvidersView,
    MetricsSummaryView,
    MetricsView,
    MetricsWorkflowsView,
    ReadyHealthView,
    TraceDetailView,
    TracesListView,
)
from api.v1.views.jobs import JobViewSet, PublishJobViewSet
from api.v1.views.providers import NewsSourceViewSet, ProviderHealthCheckViewSet
from api.v1.views.scripts import ScriptSegmentViewSet, ScriptViewSet

router = DefaultRouter()
router.register(r"articles", ArticleViewSet, basename="article")
router.register(r"tags", TagViewSet, basename="tag")
router.register(r"news-sources", NewsSourceViewSet, basename="news-source")
router.register(r"episodes", EpisodeViewSet, basename="episode")
router.register(r"scripts", ScriptViewSet, basename="script")
router.register(r"script-segments", ScriptSegmentViewSet, basename="script-segment")
router.register(r"audio-assets", AudioAssetViewSet, basename="audio-asset")
router.register(r"voice-profiles", VoiceProfileViewSet, basename="voice-profile")
router.register(
    r"persona-voice-mappings",
    PersonaVoiceMappingViewSet,
    basename="persona-voice-mapping",
)
router.register(r"publish-jobs", PublishJobViewSet, basename="publish-job")
router.register(r"jobs", JobViewSet, basename="job")
router.register(
    r"provider-health-checks",
    ProviderHealthCheckViewSet,
    basename="provider-health-check",
)
router.register(r"pipeline-runs", PipelineRunViewSet, basename="pipeline-run")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("health/live/", LiveHealthView.as_view(), name="health-live"),
    path("health/ready/", ReadyHealthView.as_view(), name="health-ready"),
    path("health/components/", ComponentsHealthView.as_view(), name="health-components"),
    path("health/celery/", CeleryHealthView.as_view(), name="health-celery"),
    path("health/llm/", LLMHealthView.as_view(), name="health-llm"),
    path("health/tts/", TTSHealthView.as_view(), name="health-tts"),
    path("health/publish/", PublishHealthView.as_view(), name="health-publish"),
    path("metrics/", MetricsView.as_view(), name="metrics"),
    path("metrics/summary/", MetricsSummaryView.as_view(), name="metrics-summary"),
    path("metrics/providers/", MetricsProvidersView.as_view(), name="metrics-providers"),
    path("metrics/jobs/", MetricsJobsView.as_view(), name="metrics-jobs"),
    path("metrics/workflows/", MetricsWorkflowsView.as_view(), name="metrics-workflows"),
    path("logs/", LogsListView.as_view(), name="logs"),
    path("logs/<uuid:event_id>/", LogDetailView.as_view(), name="logs-detail"),
    path("traces/", TracesListView.as_view(), name="traces"),
    path("traces/<str:span_id>/", TraceDetailView.as_view(), name="traces-detail"),
    path(
        "observability/dashboard/",
        DashboardSummaryView.as_view(),
        name="observability-dashboard",
    ),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("", include(router.urls)),
]
