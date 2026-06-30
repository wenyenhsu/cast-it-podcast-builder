"""Publish job and background job API views."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.request import Request
from rest_framework.response import Response

from api.v1.exceptions import ConflictError
from api.v1.filters import JobFilter, PublishJobFilter
from api.v1.mixins import RequestLoggingMixin
from api.v1.serializers.common import (
    JobAcceptedSerializer,
    JobListSerializer,
    JobSerializer,
)
from api.v1.serializers.publish import (
    PublishJobDetailSerializer,
    PublishJobListSerializer,
)
from api.v1.services.job_dispatch import ApiJobDispatchService
from apps.publish.models import PublishJob
from apps.scheduler.models import Job
from apps.scheduler.tasks.registry import get_task_for_job_type
from domain.jobs.exceptions import JobCancellationError, JobRetryError
from domain.publish.exceptions import PublishValidationError
from services.jobs.job_service import JobService
from services.publish.service import PublishService


class PublishJobViewSet(RequestLoggingMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only API for publish jobs with retry and cancel actions."""

    resource_name = "publish-job"
    queryset = PublishJob.objects.select_related("episode")
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PublishJobFilter
    ordering_fields = ["created_at", "started_at", "completed_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return PublishJobListSerializer
        return PublishJobDetailSerializer

    @extend_schema(responses={202: JobAcceptedSerializer})
    @action(detail=True, methods=["post"])
    def retry(self, request: Request, pk: str | None = None) -> Response:
        del request
        publish_job = self.get_object()
        try:
            result = PublishService().retry_publish_job(publish_job.id)
        except PublishValidationError as exc:
            raise ConflictError(detail=str(exc)) from exc
        job_id = result.publish_job_ids[-1] if result.publish_job_ids else ""
        self.log_action(
            action="retry", resource_id=str(publish_job.id), job_id=str(job_id)
        )
        return Response(
            {
                "job_id": str(job_id),
                "status": "queued",
                "detail": "Publish retry has been queued.",
                "status_url": f"/api/v1/publish-jobs/{publish_job.id}/",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={200: PublishJobDetailSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        del request
        publish_job = self.get_object()
        try:
            cancelled = PublishService().cancel_publish_job(publish_job.id)
        except PublishValidationError as exc:
            raise ConflictError(detail=str(exc)) from exc
        self.log_action(action="cancel", resource_id=str(publish_job.id))
        return Response(PublishJobDetailSerializer(cancelled).data)


class JobViewSet(RequestLoggingMixin, viewsets.ReadOnlyModelViewSet):
    """Read-only API for background jobs with retry and cancel actions."""

    resource_name = "job"
    queryset = Job.objects.all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = JobFilter
    ordering_fields = ["created_at", "updated_at", "started_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return JobListSerializer
        return JobSerializer

    @extend_schema(responses={202: JobAcceptedSerializer})
    @action(detail=True, methods=["post"])
    def retry(self, request: Request, pk: str | None = None) -> Response:
        del request
        job = self.get_object()
        service = JobService()
        dispatch = ApiJobDispatchService()
        try:
            retried = service.retry_job(job)
        except JobRetryError as exc:
            raise ConflictError(detail=str(exc)) from exc
        if get_task_for_job_type(retried.job_type) is None:
            from api.v1.exceptions import ServiceUnavailableError

            raise ServiceUnavailableError(
                detail=f"No task registered for job type '{retried.job_type}'."
            )
        retried = dispatch.redispatch(retried)
        self.log_action(action="retry", resource_id=str(job.id), job_id=str(retried.id))
        return Response(
            dispatch.build_accepted_response(
                retried,
                detail="Job retry has been queued.",
            ),
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={200: JobSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        del request
        job = self.get_object()
        try:
            cancelled = JobService().mark_cancelled(job)
        except JobCancellationError as exc:
            raise ConflictError(detail=str(exc)) from exc
        self.log_action(action="cancel", resource_id=str(job.id))
        return Response(JobSerializer(cancelled).data)
