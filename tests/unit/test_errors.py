"""Unit tests for structured HTTP errors."""

import json

from shared.errors import ErrorCode, error_response


def test_error_response_includes_correlation_id() -> None:
    response = error_response(
        error=ErrorCode.NOT_FOUND,
        message="upload session not found",
        status_code=404,
        correlation_id="corr_test123456",
    )

    assert response.status_code == 404
    body = json.loads(response.get_body())
    assert body["error"] == "not_found"
    assert body["correlation_id"] == "corr_test123456"
