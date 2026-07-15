"""Tests for operations Monitor health reporting."""

from unittest.mock import patch

import pytest

from services.admin.health import AdminHealthService
from services.publish.supabase_publisher import SupabaseHealthProbe


@pytest.mark.django_db
def test_full_report_includes_supabase() -> None:
    with patch(
        "services.publish.supabase_publisher.SupabasePublisher.probe_health",
        return_value=SupabaseHealthProbe(
            healthy=True,
            detail="REST OK · bucket=episode-audio",
            configured=True,
        ),
    ):
        report = AdminHealthService().full_report()

    names = [row["name"] for row in report]
    assert "Supabase" in names
    supabase = next(row for row in report if row["name"] == "Supabase")
    assert supabase["status"] == "Healthy"
    assert "REST OK" in supabase["detail"]


@pytest.mark.django_db
def test_supabase_not_configured_is_warning() -> None:
    with patch(
        "services.publish.supabase_publisher.SupabasePublisher.probe_health",
        return_value=SupabaseHealthProbe(
            healthy=False,
            detail="Not configured",
            configured=False,
        ),
    ):
        report = AdminHealthService().full_report()

    supabase = next(row for row in report if row["name"] == "Supabase")
    assert supabase["status"] == "Warning"
    assert supabase["detail"] == "Not configured"
