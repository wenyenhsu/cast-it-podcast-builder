"""Tests for operations datetime formatting (JaegerOS-style Django localtime)."""

from datetime import datetime, timezone as dt_timezone

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.operations.templatetags.ops_extras import local_datetime, local_datetime_title
from services.admin.time_window import local_start_of_day


@override_settings(TIME_ZONE="America/Los_Angeles")
def test_local_datetime_uses_django_timezone() -> None:
    aware = datetime(2026, 7, 1, 19, 30, tzinfo=dt_timezone.utc)
    formatted = local_datetime(aware)
    assert "Jul 1" in formatted
    assert "12:30" in formatted
    assert "PM" in formatted


@override_settings(TIME_ZONE="America/Los_Angeles")
def test_local_datetime_title_includes_timezone_name() -> None:
    aware = datetime(2026, 7, 1, 19, 30, tzinfo=dt_timezone.utc)
    title = local_datetime_title(aware)
    assert "2026" in title
    assert "PDT" in title or "PST" in title


@override_settings(TIME_ZONE="America/Los_Angeles")
def test_local_start_of_day_uses_local_midnight() -> None:
    start = local_start_of_day()
    assert start.hour == 0
    assert start.minute == 0


@pytest.mark.django_db
@override_settings(TIME_ZONE="America/Los_Angeles")
def test_failed_jobs_page_renders_local_time(admin_client) -> None:
    from django.urls import reverse

    from apps.scheduler.models import Job, JobStatus, JobType

    Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        status=JobStatus.FAILED,
        error_message="boom",
    )
    response = admin_client.get(
        reverse("operations:content"),
        {"view": "failed-jobs"},
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "PM" in content or "AM" in content
    assert "UTC" not in content
