"""Pydantic schemas for structured podcast script output."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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
    # Set by chaptered generation (never by the LLM): the source article
    # this segment discusses. Enables per-chapter audio assets.
    article_id: str | None = Field(default=None, exclude=True)

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


class CoherenceSegmentSchema(ScriptSegmentSchema):
    """Segment returned by the coherence pass with immutable ordering metadata."""

    segment_index: int = Field(ge=0)


class CoherenceScriptSchema(BaseModel):
    """Whole-episode rewrite whose segment order can be verified safely."""

    title: str
    summary: str
    segments: list[CoherenceSegmentSchema]

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
        value: list[CoherenceSegmentSchema],
    ) -> list[CoherenceSegmentSchema]:
        if not value:
            raise ValueError("Script must contain at least one segment.")
        return value


class StoryFactSchema(BaseModel):
    """A source-grounded fact that the dialogue must preserve."""

    claim: str
    evidence: str
    people: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    numbers: list[str] = Field(default_factory=list)


class StoryBriefSchema(BaseModel):
    """Structured, source-grounded representation of one article."""

    article_id: str
    title: str
    summary: str
    central_claim: str
    must_cover_facts: list[StoryFactSchema] = Field(default_factory=list)
    background: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    unsupported_topics: list[str] = Field(default_factory=list)
    possible_angles: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_grounded_content(self) -> "StoryBriefSchema":
        if not self.central_claim.strip() or not self.must_cover_facts:
            raise ValueError("Story brief requires a central claim and grounded facts.")
        return self


class EpisodeOutlineChapterSchema(BaseModel):
    """Planned narrative role and transitions for one article chapter."""

    article_id: str
    purpose: str
    must_cover_facts: list[str] = Field(default_factory=list)
    transition_in: str = ""
    transition_out: str = ""
    avoid_repeating: list[str] = Field(default_factory=list)


class EpisodeOutlineSchema(BaseModel):
    """Whole-episode plan that determines story order and throughline."""

    title: str
    throughline: str
    opening: str
    development: str
    closing: str
    article_order: list[str]
    chapters: list[EpisodeOutlineChapterSchema]

    @model_validator(mode="after")
    def order_matches_chapters(self) -> "EpisodeOutlineSchema":
        chapter_ids = [chapter.article_id for chapter in self.chapters]
        if len(set(self.article_order)) != len(self.article_order):
            raise ValueError("Outline article_order contains duplicate IDs.")
        if chapter_ids != self.article_order:
            raise ValueError("Outline chapters must follow article_order exactly.")
        return self


class ChapterCriticSchema(BaseModel):
    """Grounding and editorial evaluation for one generated chapter."""

    passed: bool
    score: int = Field(ge=0, le=100)
    missing_facts: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    repetitions: list[str] = Field(default_factory=list)
    dialogue_issues: list[str] = Field(default_factory=list)
    coherence_issues: list[str] = Field(default_factory=list)
    transition_issues: list[str] = Field(default_factory=list)
    language_matches: bool = True
    language_issues: list[str] = Field(default_factory=list)
    rewrite_instructions: list[str] = Field(default_factory=list)
