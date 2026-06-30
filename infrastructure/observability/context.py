"""Request and async correlation context propagation."""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass

from domain.observability.dtos import RequestContext
from domain.observability.exceptions import LogCorrelationError

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_job_id: ContextVar[str | None] = ContextVar("job_id", default=None)
_workflow_run_id: ContextVar[str | None] = ContextVar("workflow_run_id", default=None)
_episode_id: ContextVar[str | None] = ContextVar("episode_id", default=None)


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class ContextTokens:
    """Tokens returned when binding context for later reset."""

    correlation_id: Token[str | None]
    request_id: Token[str | None]
    job_id: Token[str | None]
    workflow_run_id: Token[str | None]
    episode_id: Token[str | None]


def get_correlation_id() -> str:
    """Return current correlation ID, generating one if missing."""
    value = _correlation_id.get()
    if value is None:
        value = _new_id()
        _correlation_id.set(value)
    return value


def get_request_id() -> str:
    """Return current request ID, generating one if missing."""
    value = _request_id.get()
    if value is None:
        value = _new_id()
        _request_id.set(value)
    return value


def get_job_id() -> str:
    return _job_id.get() or ""


def get_workflow_run_id() -> str:
    return _workflow_run_id.get() or ""


def get_episode_id() -> str:
    return _episode_id.get() or ""


def get_request_context() -> RequestContext:
    """Build the current request context snapshot."""
    return RequestContext(
        correlation_id=get_correlation_id(),
        request_id=get_request_id(),
        job_id=get_job_id(),
        workflow_run_id=get_workflow_run_id(),
        episode_id=get_episode_id(),
    )


def bind_context(
    *,
    correlation_id: str | None = None,
    request_id: str | None = None,
    job_id: str | None = None,
    workflow_run_id: str | None = None,
    episode_id: str | None = None,
) -> ContextTokens:
    """Bind observability context values for the current execution scope."""
    return ContextTokens(
        correlation_id=_correlation_id.set(correlation_id or _new_id()),
        request_id=_request_id.set(request_id or _new_id()),
        job_id=_job_id.set(job_id or ""),
        workflow_run_id=_workflow_run_id.set(workflow_run_id or ""),
        episode_id=_episode_id.set(episode_id or ""),
    )


def reset_context(tokens: ContextTokens) -> None:
    """Reset context variables to previous values."""
    _correlation_id.reset(tokens.correlation_id)
    _request_id.reset(tokens.request_id)
    _job_id.reset(tokens.job_id)
    _workflow_run_id.reset(tokens.workflow_run_id)
    _episode_id.reset(tokens.episode_id)


def set_job_id(job_id: str) -> None:
    if not job_id:
        raise LogCorrelationError("Job ID cannot be empty.")
    _job_id.set(job_id)


def set_workflow_run_id(workflow_run_id: str) -> None:
    if not workflow_run_id:
        raise LogCorrelationError("Workflow run ID cannot be empty.")
    _workflow_run_id.set(workflow_run_id)


def set_episode_id(episode_id: str) -> None:
    if not episode_id:
        raise LogCorrelationError("Episode ID cannot be empty.")
    _episode_id.set(episode_id)


def context_as_log_extra() -> dict[str, str]:
    """Return context fields suitable for structured logging."""
    ctx = get_request_context()
    extra = {
        "correlation_id": ctx.correlation_id,
        "request_id": ctx.request_id,
    }
    if ctx.job_id:
        extra["job_id"] = ctx.job_id
    if ctx.workflow_run_id:
        extra["workflow_run_id"] = ctx.workflow_run_id
    if ctx.episode_id:
        extra["episode_id"] = ctx.episode_id
    return extra
