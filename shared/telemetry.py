"""Application Insights / OpenTelemetry configuration."""

from __future__ import annotations

from typing import Any

from config import get_settings

_configured = False


def configure_telemetry() -> None:
    """Configure Azure Monitor OpenTelemetry when a connection string is present."""
    global _configured
    if _configured:
        return

    connection_string = get_settings().applicationinsights_connection_string
    if not connection_string:
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
