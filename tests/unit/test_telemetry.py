"""Unit tests for telemetry configuration."""

from unittest.mock import patch

import pytest

from shared.telemetry import configure_telemetry, reset_telemetry, set_operation_attributes


def test_configure_telemetry_skips_without_connection_string(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_telemetry()
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    from config import get_settings

    get_settings.cache_clear()

    with patch("azure.monitor.opentelemetry.configure_azure_monitor") as mock_configure:
        configure_telemetry()

    mock_configure.assert_not_called()


def test_configure_telemetry_enables_azure_monitor(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_telemetry()
    monkeypatch.setenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "InstrumentationKey=test-key",
    )
    from config import get_settings

    get_settings.cache_clear()

    with patch("azure.monitor.opentelemetry.configure_azure_monitor") as mock_configure:
        configure_telemetry()

    mock_configure.assert_called_once()
    assert mock_configure.call_args.kwargs["instrumentation_options"]["azure_sdk"]["enabled"]


def test_set_operation_attributes_noop_without_span() -> None:
    set_operation_attributes(route_id="route-1", correlation_id="corr-1")
