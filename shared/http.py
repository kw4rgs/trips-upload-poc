"""HTTP response helpers for Azure Functions handlers."""

from __future__ import annotations

import json
from typing import Any

import azure.functions as func
from pydantic import BaseModel


def json_response(
    body: dict[str, Any] | BaseModel,
    *,
    status_code: int = 200,
) -> func.HttpResponse:
    """Return a JSON HttpResponse."""
    if isinstance(body, BaseModel):
        payload = body.model_dump_json()
    else:
        payload = json.dumps(body)

    return func.HttpResponse(
        body=payload,
        mimetype="application/json",
        status_code=status_code,
    )
