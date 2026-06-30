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
    path("health/celery/", CeleryHealthView.as_view(), name="health-celery"),
    path("health/llm/", LLMHealthView.as_view(), name="health-llm"),
    path("health/tts/", TTSHealthView.as_view(), name="health-tts"),
    path("health/publish/", PublishHealthView.as_view(), name="health-publish"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("", include(router.urls)),
]
