# Script Validation Rules (v1.0.0)

A valid podcast script must satisfy all of the following:

1. **Schema**: JSON object with `title`, `summary`, and `segments` array.
2. **Segments**: Each segment includes `speaker`, `voice`, `emotion`, `text`, `pause_before_seconds`, and `pause_after_seconds`.
3. **Speakers**: Must include both `expert` and `beginner` speakers in the dialogue.
4. **Text**: No segment may have empty `text`.
5. **Flow**: Dialogue should alternate between expert and beginner with natural transitions.
6. **Coverage**: Script must reflect the provided articles without excessive repetition.
7. **Pauses**: Pause values must be non-negative numbers (seconds).
8. **Optional segments**: Use `intro`, `outro`, or `narration` only when explicitly requested.

Reject invalid structures. Never return partial or free-form text.
