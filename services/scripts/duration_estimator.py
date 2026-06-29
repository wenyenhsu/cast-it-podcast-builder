"""Duration estimation for podcast script segments."""

from domain.scripts.schema import ScriptSegmentSchema


def estimate_segment_duration_seconds(
    segment: ScriptSegmentSchema,
    *,
    words_per_minute: int = 150,
) -> int:
    """Estimate spoken duration for a single segment including pauses."""
    word_count = len(segment.text.split())
    speech_seconds = (word_count / words_per_minute) * 60
    total = speech_seconds + segment.pause_before_seconds + segment.pause_after_seconds
    return max(1, int(round(total)))


def estimate_total_duration_seconds(
    segments: list[ScriptSegmentSchema],
    *,
    words_per_minute: int = 150,
) -> int:
    """Estimate total spoken duration for all segments."""
    return sum(
        estimate_segment_duration_seconds(segment, words_per_minute=words_per_minute)
        for segment in segments
    )
