"""Shared fixtures for admin tests."""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import Group, User
from django.test import Client

from apps.providers.models import NewsSource, ProviderType
from services.admin.permissions import (
    ROLE_ADMINISTRATOR,
    ROLE_OPERATOR,
    ROLE_REVIEWER,
)


@pytest.fixture
def staff_user(db: None) -> User:
    user = User.objects.create_user(
        username="ops-admin",
        email="ops@example.com",
        password="test-pass-123",
        is_staff=True,
        is_superuser=True,
    )
    admin_group, _ = Group.objects.get_or_create(name=ROLE_ADMINISTRATOR)
    user.groups.add(admin_group)
    return user


@pytest.fixture
def operator_user(db: None) -> User:
    user = User.objects.create_user(
        username="ops-operator",
        email="operator@example.com",
        password="test-pass-123",
        is_staff=True,
    )
    operator_group, _ = Group.objects.get_or_create(name=ROLE_OPERATOR)
    user.groups.add(operator_group)
    return user


@pytest.fixture
def reviewer_user(db: None) -> User:
    user = User.objects.create_user(
        username="ops-reviewer",
        email="reviewer@example.com",
        password="test-pass-123",
        is_staff=True,
    )
    reviewer_group, _ = Group.objects.get_or_create(name=ROLE_REVIEWER)
    user.groups.add(reviewer_group)
    return user


@pytest.fixture
def admin_client(staff_user: User) -> Client:
    client = Client()
    client.force_login(staff_user)
    return client


@pytest.fixture
def news_source(db: None) -> NewsSource:
    return NewsSource.objects.create(
        name="Tech RSS",
        provider_type=ProviderType.RSS,
        rss_url="https://example.com/feed.xml",
        language="en",
        enabled=True,
    )


@pytest.fixture
def mock_celery_task() -> MagicMock:
    task = MagicMock()
    async_result = MagicMock()
    async_result.id = "celery-task-id-123"
    task.delay.return_value = async_result
    return task


@pytest.fixture
def mock_job_dispatch(mock_celery_task: MagicMock):
    with patch(
        "api.v1.services.job_dispatch.get_task_for_job_type",
        return_value=mock_celery_task,
    ):
        yield mock_celery_task
