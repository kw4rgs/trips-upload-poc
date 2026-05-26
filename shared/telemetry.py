"""Application Insights / OpenTelemetry configuration."""

from __future__ import annotations

import re
from typing import Any

from config import get_settings
from shared.logging import get_logger

_configured = False
_logger = get_logger(__name__)

# Same UUID check as azure-monitor-opentelemetry exporter.
_INSTRUMENTATION_KEY_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def _is_valid_applicationinsights_connection_string(connection_string: str) -> bool:
    """Return True when the connection string has a valid instrumentation key UUID."""
    pairs = dict(item.split("=", 1) for item in connection_string.split(";") if "=" in item)
    instrumentation_key = pairs.get("InstrumentationKey") or pairs.get("instrumentationkey")
    if not instrumentation_key:
        return False
    return _INSTRUMENTATION_KEY_PATTERN.match(instrumentation_key) is not None


def configure_telemetry() -> None:
    """Configure Azure Monitor OpenTelemetry when a connection string is present."""
    global _configured
    if _configured:
        return

    connection_string = get_settings().applicationinsights_connection_string.strip()
    if not connection_string:
        return

    if not _is_valid_applicationinsights_connection_string(connection_string):
        _logger.warning(
            {
                "message": "Skipping Application Insights telemetry: invalid connection string",
                "hint": "Unset APPLICATIONINSIGHTS_CONNECTION_STRING locally or use a valid App Insights connection string",
            }
        )
        return

    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(
        connection_string=connection_string,
        instrumentation_options={
            "azure_sdk": {"enabled": True},
        },
    )
    _configured = True


def reset_telemetry() -> None:
    """Reset telemetry configuration (used in tests)."""
    global _configured
    _configured = False


def set_operation_attributes(**attributes: Any) -> None:
    """Attach custom dimensions to the current OpenTelemetry span."""
    from opentelemetry import trace

    span = trace.get_current_span()
    if not span.is_recording():
        return

    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, str(value))
