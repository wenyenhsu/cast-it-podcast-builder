"""Base TTS provider interface."""

from abc import ABC, abstractmethod

from domain.audio.dtos import ProviderCapabilities, TTSRequest, TTSResponse, VoiceInfo


class BaseTTSProvider(ABC):
    """Abstract adapter that every TTS provider must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier."""

    @abstractmethod
    def generate_segment(self, request: TTSRequest) -> TTSResponse:
        """Generate audio for a single text segment."""

    @abstractmethod
    def list_voices(self) -> list[VoiceInfo]:
        """Return available voices from the provider."""

    @abstractmethod
    def health_check(self) -> bool:
        """Verify the provider is reachable and ready."""

    @abstractmethod
    def estimate_duration(self, text: str, *, speed: float = 1.0) -> float:
        """Estimate spoken duration in seconds for the given text."""

    @abstractmethod
    def supported_languages(self) -> list[str]:
        """Return languages supported by the provider."""

    @abstractmethod
    def supported_formats(self) -> list[str]:
        """Return audio formats supported by the provider."""

    def capabilities(self) -> ProviderCapabilities:
        """Return normalized provider capabilities."""
        return ProviderCapabilities(
            provider=self.provider_name,
            languages=tuple(self.supported_languages()),
            formats=tuple(self.supported_formats()),
            healthy=self.health_check(),
        )
