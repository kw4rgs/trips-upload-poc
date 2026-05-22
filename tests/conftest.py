"""Shared pytest fixtures for trips-upload-poc."""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

import pytest
from azure.functions import HttpRequest

from config import Settings, get_settings
from shared.correlation import reset_correlation_id
from shared.logging import reset_logging


@pytest.fixture(autouse=True)
def _isolated_telemetry() -> Generator[None, None, None]:
    """Reset telemetry configuration between tests."""
    from shared.telemetry import reset_telemetry

    reset_telemetry()
    yield
    reset_telemetry()


@pytest.fixture(autouse=True)
def _isolated_logging() -> Generator[None, None, None]:
    """Reset structured logging handlers between tests."""
    reset_logging()
    yield
    reset_logging()


@pytest.fixture(autouse=True)
def _isolated_settings_cache() -> Generator[None, None, None]:
    """Clear cached settings between tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _isolated_correlation_id() -> Generator[None, None, None]:
    """Reset correlation context between tests."""
    reset_correlation_id()
    yield
    reset_correlation_id()


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Return Settings loaded from deterministic test env vars."""
    monkeypatch.setenv("STORAGE_ACCOUNT_NAME", "teststorage")
    monkeypatch.setenv("STORAGE_CONTAINER", "landing")
    monkeypatch.setenv("COSMOS_ENDPOINT", "https://test.documents.azure.com:443/")
    monkeypatch.setenv("COSMOS_DATABASE", "trips")
    monkeypatch.setenv("COSMOS_CONTAINER", "trip_ingestion_log")
    monkeypatch.setenv("EVENTHUB_NAME", "trip-processing-eventhub")
    monkeypatch.setenv(
        "EVENTHUB_FULLY_QUALIFIED_NAMESPACE",
        "test.servicebus.windows.net",
    )
    monkeypatch.setenv("JWT_MOCK_SECRET", "test-secret-thirty-two-characters-long!")
    monkeypatch.setenv("JWT_MOCK_USER_ID", "user-test")
    monkeypatch.setenv("SAS_TTL_MINUTES", "15")
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def auth_token(settings):
    """Return a valid Bearer authorization header for tests."""
    from services.auth import create_mock_token

    token = create_mock_token(settings.jwt_mock_user_id, settings.jwt_mock_secret)
    return f"Bearer {token}"


@pytest.fixture
def http_request_factory():
    """Build Azure Functions HttpRequest objects for handler tests."""

    def _factory(
        *,
        method: str = "GET",
        url: str = "/api/health",
        headers: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> HttpRequest:
        return HttpRequest(
            method=method,
            url=url,
            headers=headers or {},
            params={},
            body=body,
        )

    return _factory


@pytest.fixture
def parse_json_log():
    """Parse a single structured JSON log line from captured stdout."""

    def _parse(output: str) -> dict[str, Any]:
        lines = [line for line in output.strip().splitlines() if line.strip()]
        assert lines, "expected at least one log line"
        return json.loads(lines[-1])

    return _parse
