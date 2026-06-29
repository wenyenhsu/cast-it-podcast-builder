"""News ingestion provider configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration passed to news providers via dependency injection."""

    source_name: str
    provider_type: str
    language: str = "en"
    rss_url: str = ""
    homepage: str = ""
    api_key: str = ""
    extra: dict[str, str] | None = None
