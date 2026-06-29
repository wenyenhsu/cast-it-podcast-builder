"""Tests for LLM domain exceptions."""

from domain.llm.exceptions import (
    InvalidResponseException,
    LLMException,
    PromptTooLargeException,
    ProviderUnavailableException,
    TimeoutException,
)


class TestLLMExceptions:
    def test_exception_hierarchy(self) -> None:
        assert issubclass(ProviderUnavailableException, LLMException)
        assert issubclass(InvalidResponseException, LLMException)
        assert issubclass(PromptTooLargeException, LLMException)
        assert issubclass(TimeoutException, LLMException)

    def test_exception_messages(self) -> None:
        exc = ProviderUnavailableException("Server down")
        assert str(exc) == "Server down"
