"""Tests for prompt builder."""

from pathlib import Path

import pytest

from services.llm.prompt_builder import PromptBuilder


@pytest.fixture
def templates_dir(tmp_path: Path) -> Path:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "system.md").write_text(
        "You are a podcast host for {show_name}. Language: {language}.",
        encoding="utf-8",
    )
    (prompts_dir / "summarize.md").write_text(
        "Summarize: {content}",
        encoding="utf-8",
    )
    return prompts_dir


class TestPromptBuilder:
    def test_load_template(self, templates_dir: Path) -> None:
        builder = PromptBuilder(templates_dir=templates_dir)
        content = builder.load_template("system")
        assert "{show_name}" in content

    def test_render_substitutes_variables(self, templates_dir: Path) -> None:
        builder = PromptBuilder(templates_dir=templates_dir)
        rendered = builder.render(
            "Hello {name}, welcome to {show}.",
            {"name": "Alice", "show": "Cast It"},
        )
        assert rendered == "Hello Alice, welcome to Cast It."

    def test_build_system_prompt(self, templates_dir: Path) -> None:
        builder = PromptBuilder(templates_dir=templates_dir)
        prompt = builder.build_system_prompt(
            "system",
            {"show_name": "Cast It", "language": "en"},
        )
        assert "Cast It" in prompt
        assert "Language: en" in prompt

    def test_build_user_prompt(self, templates_dir: Path) -> None:
        builder = PromptBuilder(templates_dir=templates_dir)
        prompt = builder.build_user_prompt("summarize", {"content": "Article body"})
        assert prompt == "Summarize: Article body"

    def test_missing_template_raises(self, templates_dir: Path) -> None:
        builder = PromptBuilder(templates_dir=templates_dir)
        with pytest.raises(FileNotFoundError):
            builder.load_template("nonexistent")

    def test_unknown_variable_left_unchanged(self, templates_dir: Path) -> None:
        builder = PromptBuilder(templates_dir=templates_dir)
        assert builder.render("Hello {name}", {"name": "Alice"}) == "Hello Alice"
        assert "{missing}" in builder.render("Value: {missing}", {})
