"""Audio generation exceptions."""


class TTSException(Exception):
    """Base exception for text-to-speech operations."""


class VoiceNotFoundException(TTSException):
    """Raised when a requested voice profile or provider voice is not found."""


class ProviderUnavailableException(TTSException):
    """Raised when the TTS provider is unreachable or unhealthy."""


class UnsupportedLanguageException(TTSException):
    """Raised when the requested language is not supported by the provider."""


class UnsupportedFormatException(TTSException):
    """Raised when the requested audio format is not supported."""


class AudioGenerationException(TTSException):
    """Raised when segment audio generation fails."""
