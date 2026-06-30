"""Tests for admin role permissions."""

import pytest
from django.contrib.admin.sites import AdminSite

from apps.core.admin.mixins import AdminRolePermissionMixin
from apps.scheduler.admin import JobAdmin
from apps.scheduler.models import Job
from services.admin.permissions import (
    ROLE_OPERATOR,
    ensure_admin_roles,
    is_administrator,
    is_operator,
    is_reviewer,
    user_has_role,
)


class _SampleAdmin(AdminRolePermissionMixin):
    operator_only_actions = ("delete_completed_jobs",)

    def all_actions(self) -> dict[str, tuple[str, None, None]]:
        return {
            "delete_completed_jobs": ("Delete", None, None),
            "retry_failed_jobs": ("Retry", None, None),
        }

    def get_actions(self, request):
        return self.filter_actions_for_role(request, self.all_actions())


@pytest.mark.django_db
def test_admin_roles_created() -> None:
    ensure_admin_roles()
    from django.contrib.auth.models import Group

    names = set(Group.objects.values_list("name", flat=True))
    assert ROLE_OPERATOR in names


@pytest.mark.django_db
def test_role_helpers(staff_user, operator_user, reviewer_user) -> None:
    assert is_administrator(staff_user)
    assert is_operator(operator_user)
    assert is_reviewer(reviewer_user)
    assert user_has_role(operator_user, ROLE_OPERATOR)


@pytest.mark.django_db
def test_reviewer_cannot_see_operator_actions(reviewer_user) -> None:
    from django.test import RequestFactory

    admin = _SampleAdmin()
    request = RequestFactory().get("/")
    request.user = reviewer_user
    actions = admin.get_actions(request)
    assert "delete_completed_jobs" not in actions
    assert "retry_failed_jobs" in actions


@pytest.mark.django_db
def test_job_admin_changelist_loads(admin_client) -> None:
    response = admin_client.get("/admin/scheduler/job/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_registered_model_admins() -> None:
    site = AdminSite()
    job_admin = JobAdmin(Job, site)
    assert job_admin.list_display[0] == "job_type"
