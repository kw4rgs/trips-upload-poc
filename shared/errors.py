"""Structured HTTP error responses."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import azure.functions as func
from pydantic import BaseModel, ConfigDict, Field

from shared.http import json_response


class ErrorCode(StrEnum):
    """Canonical API error codes."""

    UNAUTHORIZED = "unauthorized"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    SERVICE_UNAVAILABLE = "service_unavailable"


class ErrorResponse(BaseModel):
    """Standard JSON error envelope."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorCode
    message: str
    correlation_id: str | None = None
    details: Any | None = None


def error_response(
    *,
    error: ErrorCode,
    message: str,
    status_code: int,
    correlation_id: str | None = None,
    details: Any | None = None,
) -> func.HttpResponse:
    """Return a structured error HttpResponse."""
    body = ErrorResponse(
        error=error,
        message=message,
        correlation_id=correlation_id,
        details=details,
    )
    return json_response(body, status_code=status_code)
