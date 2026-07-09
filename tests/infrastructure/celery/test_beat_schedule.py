"""Tests for Celery beat schedule configuration."""

import pytest

from domain.jobs.exceptions import SchedulerConfigurationError
from infrastructure.celery.beat_schedule import (
    build_beat_schedule,
    parse_cron_expression,
)


def test_parse_cron_expression_valid() -> None:
    schedule = parse_cron_expression("0 6 * * *")
    assert schedule._orig_minute == "0"  # type: ignore[attr-defined]
    assert schedule._orig_hour == "6"  # type: ignore[attr-defined]


def test_parse_cron_expression_invalid() -> None:
    with pytest.raises(SchedulerConfigurationError):
        parse_cron_expression("invalid")


def test_build_beat_schedule_contains_required_jobs() -> None:
    schedule = build_beat_schedule()
    assert "daily-news-import" in schedule
    assert "daily-episode-planning" in schedule
    assert "daily-script-generation" in schedule
    assert "daily-supabase-publish" in schedule
    assert "failed-job-retry-sweep" in schedule
    assert schedule["daily-news-import"]["task"].endswith("import_news_scheduled")
