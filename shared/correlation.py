"""Correlation ID generation and request-scoped propagation."""

import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def generate_correlation_id() -> str:
    """Create a new correlation identifier."""
    return f"corr_{uuid.uuid4().hex[:12]}"


def get_correlation_id() -> str | None:
    """Return the correlation ID bound to the current execution context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Bind a correlation ID to the current execution context."""
    _correlation_id.set(correlation_id)


def reset_correlation_id() -> None:
    """Clear correlation ID from the current execution context."""
    _correlation_id.set(None)


def bind_correlation_id(correlation_id: str | None = None) -> str:
    """Ensure a correlation ID exists in context and return it."""
    resolved = correlation_id or get_correlation_id() or generate_correlation_id()
    set_correlation_id(resolved)
    return resolved
