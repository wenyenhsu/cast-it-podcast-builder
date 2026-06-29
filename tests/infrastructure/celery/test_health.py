"""Tests for Celery health service."""

from infrastructure.celery.health import CeleryHealthService


class MockInspect:
    def ping(self) -> dict[str, dict[str, str]]:
        return {"worker1": {"ok": "pong"}}

    def registered(self) -> dict[str, list[str]]:
        return {
            "worker1": [
                "scheduler.tasks.import_news.import_news_task",
                "scheduler.tasks.planning.episode_planning_task",
                "scheduler.tasks.script.generate_script_task",
                "scheduler.tasks.audio.generate_audio_task",
                "scheduler.tasks.pipeline.run_audio_pipeline_task",
                "scheduler.tasks.publish.publish_episode_task",
                "scheduler.tasks.monitoring.retry_failed_jobs_task",
                "scheduler.tasks.monitoring.provider_health_check_task",
                "scheduler.tasks.summarize.summarize_article_task",
                "scheduler.tasks.classify.classify_article_task",
            ]
        }


def test_health_check_all_with_mock_inspect() -> None:
    service = CeleryHealthService(inspect_client=MockInspect())
    results = service.check_all()
    assert results["workers"] is True
    assert results["task_registration"] is True


def test_health_check_workers_unavailable() -> None:
    class EmptyInspect:
        def ping(self) -> dict[str, dict[str, str]] | None:
            return None

        def registered(self) -> dict[str, list[str]] | None:
            return None

    service = CeleryHealthService(inspect_client=EmptyInspect())
    assert service.check_workers() is False
