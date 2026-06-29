"""Article classification categories."""

from enum import StrEnum


class ArticleCategory(StrEnum):
    """Supported article classification categories."""

    AI = "AI"
    PROGRAMMING = "Programming"
    CLOUD = "Cloud"
    SECURITY = "Security"
    DEVOPS = "DevOps"
    DATA = "Data"
    STARTUP = "Startup"
    OPEN_SOURCE = "Open Source"
    OTHER = "Other"

    @classmethod
    def from_label(cls, label: str) -> "ArticleCategory":
        """Resolve a category from an LLM label with fallback to Other."""
        normalized = label.strip()
        for member in cls:
            if member.value.lower() == normalized.lower():
                return member
        aliases = {
            "opensource": cls.OPEN_SOURCE,
            "open-source": cls.OPEN_SOURCE,
            "dev ops": cls.DEVOPS,
        }
        return aliases.get(normalized.lower(), cls.OTHER)
