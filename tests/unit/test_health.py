"""Unit tests for health HTTP blueprint."""

import json

from api.v1.health import health


def test_health_returns_ok(http_request_factory) -> None:
    response = health(http_request_factory())

    assert response.status_code == 200
    assert response.mimetype == "application/json"

    body = json.loads(response.get_body())
    assert body["status"] == "ok"
    assert body["service"] == "trips-upload-poc"
    assert body["correlation_id"].startswith("corr_")


def test_health_uses_request_correlation_id(http_request_factory) -> None:
    response = health(
        http_request_factory(headers={"x-correlation-id": "corr_from_header1"}),
    )

    body = json.loads(response.get_body())
    assert body["correlation_id"] == "corr_from_header1"
