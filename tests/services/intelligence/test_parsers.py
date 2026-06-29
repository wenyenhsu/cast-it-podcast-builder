"""Tests for intelligence response parsers."""

import pytest

from services.intelligence.parsers import (
    parse_integer_response,
    parse_keywords,
    parse_single_line,
)


class TestParsers:
    def test_parse_integer_response(self) -> None:
        assert parse_integer_response("Score: 87", minimum=0, maximum=100) == 87
        assert parse_integer_response("150", minimum=0, maximum=100) == 100

    def test_parse_integer_response_invalid(self) -> None:
        with pytest.raises(ValueError):
            parse_integer_response("no number", minimum=0, maximum=100)

    def test_parse_single_line(self) -> None:
        assert parse_single_line("  AI\nextra") == "AI"

    def test_parse_keywords_comma_separated(self) -> None:
        keywords = parse_keywords("Python, Django, AI, python", minimum=2, maximum=10)
        assert keywords == ["Python", "Django", "AI"]

    def test_parse_keywords_json(self) -> None:
        keywords = parse_keywords('["cloud", "kubernetes"]', minimum=1, maximum=10)
        assert keywords == ["cloud", "kubernetes"]
