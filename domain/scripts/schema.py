"""Pydantic schemas for structured podcast script output."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

SpeakerLiteral = Literal["expert", "beginner", "narration", "intro", "outro"]

REQUIRED_SPEAKERS = frozenset({"expert", "beginner"})


class ScriptSegmentSchema(BaseModel):
    """Validated segment within a podcast script."""

    speaker: SpeakerLiteral
    voice: str = ""
    emotion: str = ""
    text: str
    pause_before_seconds: float = Field(default=0.0, ge=0)
    pause_after_seconds: float = Field(default=0.0, ge=0)

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Segment text must not be empty.")
        return value.strip()


class PodcastScriptSchema(BaseModel):
    """Validated full podcast script returned by the LLM."""

    title: str
    summary: str
    segments: list[ScriptSegmentSchema]

    @field_validator("title", "summary")
    @classmethod
    def fields_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Title and summary must not be empty.")
        return value.strip()

    @field_validator("segments")
    @classmethod
    def segments_must_not_be_empty(
        cls,
        value: list[ScriptSegmentSchema],
    ) -> list[ScriptSegmentSchema]:
        if not value:
            raise ValueError("Script must contain at least one segment.")
        return value
