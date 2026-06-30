"""Shared Django Admin mixins."""

from typing import Any

from django.contrib import messages
from django.db.models import QuerySet
from django.http import HttpRequest

from services.admin.action_logger import AdminActionLogger
from services.admin.actions import AdminOperationsService
from services.admin.dispatch import AdminJobDispatchService
from services.admin.permissions import is_operator, is_reviewer


class AdminActionMixin:
    """Mixin providing admin action helpers."""

    action_service: AdminOperationsService = AdminOperationsService()
    dispatch_service: AdminJobDispatchService = AdminJobDispatchService()
    action_logger: AdminActionLogger = AdminActionLogger()

    def _user_id(self, request: HttpRequest) -> int | None:
        user = request.user
        if user.is_authenticated:
            return int(user.pk)
        return None

    def _message_jobs(
        self,
        request: HttpRequest,
        job_ids: list[str],
        *,
        detail: str,
    ) -> None:
        if not job_ids:
            messages.warning(request, "No jobs were queued.")
            return
        messages.success(
            request,
            f"{detail} Queued {len(job_ids)} job(s): {', '.join(job_ids[:5])}",
        )

    def _selected_ids(self, queryset: QuerySet[Any]) -> list[str]:
        return [str(obj.pk) for obj in queryset]

    def _require_operator(self, request: HttpRequest) -> bool:
        if is_operator(request.user):
            return True
        messages.error(request, "Operator permissions required for this action.")
        return False


class AdminRolePermissionMixin:
    """Restricts destructive admin actions to operators."""

    operator_only_actions: tuple[str, ...] = ()

    def filter_actions_for_role(
        self,
        request: HttpRequest,
        actions: dict[str, Any],
    ) -> dict[str, Any]:
        if is_operator(request.user):
            return actions
        if is_reviewer(request.user):
            return {
                name: action
                for name, action in actions.items()
                if name not in self.operator_only_actions
            }
        return {}

    def get_actions(self, request: HttpRequest) -> dict[str, Any]:
        actions = super().get_actions(request)  # type: ignore[misc]
        return self.filter_actions_for_role(request, actions)
