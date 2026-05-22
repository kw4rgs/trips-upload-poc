"""Structured JSON logging for Azure Functions."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from shared.correlation import get_correlation_id

_CONFIGURED = False


class StructuredJsonFormatter(logging.Formatter):
    """Emit one JSON object per log line for App Insights ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
        }

        if isinstance(record.msg, dict):
            payload.update(record.msg)
        else:
            payload["message"] = record.getMessage()

        correlation_id = get_correlation_id()
        if correlation_id and "correlation_id" not in payload:
            payload["correlation_id"] = correlation_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logger with structured JSON output to stdout."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured for structured JSON output."""
    configure_logging()
    return logging.getLogger(name)
