"""Tests for script duration estimation."""

from domain.scripts.schema import ScriptSegmentSchema
from services.scripts.duration_estimator import (
    estimate_segment_duration_seconds,
    estimate_total_duration_seconds,
)


def test_estimate_segment_duration_includes_pauses() -> None:
    segment = ScriptSegmentSchema(
        speaker="expert",
        voice="expert_voice",
        emotion="calm",
        text="one two three four five six seven eight nine ten",
        pause_before_seconds=1.0,
        pause_after_seconds=2.0,
    )
    duration = estimate_segment_duration_seconds(segment, words_per_minute=150)
    assert duration >= 4


def test_estimate_total_duration_sums_segments() -> None:
    segments = [
        ScriptSegmentSchema(
            speaker="expert",
            voice="expert_voice",
            emotion="calm",
            text="Short expert line with several words here.",
            pause_before_seconds=0,
            pause_after_seconds=0,
        ),
        ScriptSegmentSchema(
            speaker="beginner",
            voice="beginner_voice",
            emotion="curious",
            text="Short beginner line with several words here too.",
            pause_before_seconds=0,
            pause_after_seconds=0,
        ),
    ]
    total = estimate_total_duration_seconds(segments, words_per_minute=150)
    assert total == sum(
        estimate_segment_duration_seconds(segment, words_per_minute=150)
        for segment in segments
    )
