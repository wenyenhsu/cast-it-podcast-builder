"""Shared helpers for content intelligence services."""

import json
import re


def parse_integer_response(content: str, *, minimum: int, maximum: int) -> int:
    """Extract an integer from an LLM response and clamp to range."""
    match = re.search(r"-?\d+", content.strip())
    if not match:
        raise ValueError("LLM response did not contain an integer.")
    value = int(match.group())
    return max(minimum, min(maximum, value))


def parse_single_line(content: str) -> str:
    """Return the first non-empty line from an LLM response."""
    for line in content.strip().splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return content.strip()


def parse_keywords(content: str, *, minimum: int, maximum: int) -> list[str]:
    """Parse comma-separated or JSON keyword lists from an LLM response."""
    stripped = content.strip()
    keywords: list[str] = []

    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                keywords = [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            keywords = []

    if not keywords:
        keywords = [part.strip() for part in stripped.split(",") if part.strip()]

    deduplicated: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        normalized = keyword.lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduplicated.append(keyword)

    if len(deduplicated) < minimum:
        return deduplicated[:maximum]

    return deduplicated[:maximum]
