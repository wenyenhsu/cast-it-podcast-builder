"""Performance tracking tests."""

from services.observability.performance import PerformanceTracker


def test_performance_tracker_records_stats() -> None:
    tracker = PerformanceTracker()
    with tracker.track("api_request"):
        pass
    summary = tracker.summary()
    assert "api_request" in summary
    assert summary["api_request"]["count"] == 1
    assert summary["api_request"]["avg_ms"] >= 0
