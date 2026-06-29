"""LLM domain exceptions."""


class LLMException(Exception):
    """Base exception for LLM operations."""


class ProviderUnavailableException(LLMException):
    """Raised when the LLM provider cannot be reached."""


class InvalidResponseException(LLMException):
    """Raised when the provider returns an unexpected or malformed response."""


class PromptTooLargeException(LLMException):
    """Raised when the prompt exceeds configured size limits."""


class TimeoutException(LLMException):
    """Raised when an LLM request exceeds the configured timeout."""
