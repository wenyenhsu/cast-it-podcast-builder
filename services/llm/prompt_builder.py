"""Prompt template builder for LLM requests."""

from pathlib import Path

from django.conf import settings


class PromptBuilder:
    """Loads and renders prompt templates with variable substitution."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
        self._templates_dir = templates_dir or (base_dir / "templates" / "prompts")

    def load_template(self, name: str) -> str:
        """Load a template file by name without the .md extension."""
        path = self._templates_dir / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {name}")
        return path.read_text(encoding="utf-8")

    def render(self, template: str, variables: dict[str, str] | None = None) -> str:
        """Render a template string with the given variables."""
        safe_vars = variables or {}
        try:
            return template.format_map(_SafeFormatDict(safe_vars))
        except KeyError as exc:
            raise ValueError(f"Missing template variable: {exc}") from exc

    def build_system_prompt(
        self,
        template_name: str,
        variables: dict[str, str] | None = None,
    ) -> str:
        """Build a system prompt from a named template."""
        template = self.load_template(template_name)
        return self.render(template, variables).strip()

    def build_user_prompt(
        self,
        template_name: str,
        variables: dict[str, str] | None = None,
    ) -> str:
        """Build a user prompt from a named template."""
        template = self.load_template(template_name)
        return self.render(template, variables).strip()


class _SafeFormatDict(dict[str, str]):
    """Dict that leaves unknown placeholders unchanged during format_map."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
