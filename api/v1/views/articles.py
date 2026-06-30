"""Article and tag API views."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.request import Request
from rest_framework.response import Response

from api.v1.filters import ArticleFilter, TagFilter
from api.v1.mixins import RequestLoggingMixin
from api.v1.serializers.articles import (
    ArticleDetailSerializer,
    ArticleImportSerializer,
    ArticleListSerializer,
    ArticleWriteSerializer,
    TagSerializer,
)
from api.v1.serializers.common import JobAcceptedSerializer
from api.v1.services.job_dispatch import ApiJobDispatchService
from apps.articles.models import Article, Tag
from apps.scheduler.models import JobType


class TagViewSet(RequestLoggingMixin, viewsets.ModelViewSet):
    """CRUD API for article tags."""

    resource_name = "tag"
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = TagFilter
    search_fields = ["name", "slug"]
    ordering_fields = ["name"]
    ordering = ["name"]


class ArticleViewSet(RequestLoggingMixin, viewsets.ModelViewSet):
    """CRUD API for news articles with async intelligence actions."""

    resource_name = "article"
    queryset = Article.objects.select_related("source").prefetch_related("tags")
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ArticleFilter
    search_fields = ["title", "author", "url", "source__name"]
    ordering_fields = [
        "created_at",
        "updated_at",
        "published_at",
        "importance_score",
    ]
    ordering = ["-published_at", "-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ArticleListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return ArticleWriteSerializer
        return ArticleDetailSerializer

    @extend_schema(
        request=ArticleImportSerializer,
        responses={202: JobAcceptedSerializer},
        summary="Import news articles asynchronously",
    )
    @action(detail=False, methods=["post"], url_path="import")
    def import_articles(self, request: Request) -> Response:
        serializer = ArticleImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload: dict[str, str] = {}
        source_id = serializer.validated_data.get("source_id")
        if source_id:
            payload["source_id"] = str(source_id)
        job = ApiJobDispatchService().dispatch(JobType.IMPORT_NEWS, payload)
        self.log_action(action="import", job_id=str(job.id))
        return Response(
            ApiJobDispatchService().build_accepted_response(job),
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={202: JobAcceptedSerializer})
    @action(detail=True, methods=["post"])
    def summarize(self, request: Request, pk: str | None = None) -> Response:
        del request
        article = self.get_object()
        job = ApiJobDispatchService().dispatch(
            JobType.SUMMARIZE_ARTICLE,
            {"article_id": str(article.id)},
        )
        self.log_action(
            action="summarize", resource_id=str(article.id), job_id=str(job.id)
        )
        return Response(
            ApiJobDispatchService().build_accepted_response(job),
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={202: JobAcceptedSerializer})
    @action(detail=True, methods=["post"])
    def classify(self, request: Request, pk: str | None = None) -> Response:
        del request
        article = self.get_object()
        job = ApiJobDispatchService().dispatch(
            JobType.CLASSIFY_ARTICLE,
            {"article_id": str(article.id)},
        )
        self.log_action(
            action="classify", resource_id=str(article.id), job_id=str(job.id)
        )
        return Response(
            ApiJobDispatchService().build_accepted_response(job),
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        responses={202: JobAcceptedSerializer},
        summary="Extract keywords asynchronously",
    )
    @action(detail=True, methods=["post"], url_path="extract-keywords")
    def extract_keywords(self, request: Request, pk: str | None = None) -> Response:
        del request
        article = self.get_object()
        job = ApiJobDispatchService().dispatch(
            JobType.CLASSIFY_ARTICLE,
            {"article_id": str(article.id), "operation": "extract_keywords"},
        )
        self.log_action(
            action="extract_keywords",
            resource_id=str(article.id),
            job_id=str(job.id),
        )
        return Response(
            ApiJobDispatchService().build_accepted_response(
                job,
                detail="Keyword extraction has been queued.",
            ),
            status=status.HTTP_202_ACCEPTED,
        )
