"""Unit tests for structured logging."""

import json

from shared.correlation import bind_correlation_id
from shared.logging import get_logger


def test_logger_emits_json_with_correlation_id(
    capsys,
    parse_json_log,
) -> None:
    bind_correlation_id("corr_logtest12345")
    logger = get_logger("tests.logging")

    logger.info(
        {
            "operation": "unit_test",
            "status": "SUCCESS",
            "route_id": "route-1",
        },
    )

    payload = parse_json_log(capsys.readouterr().out)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "tests.logging"
    assert payload["operation"] == "unit_test"
    assert payload["status"] == "SUCCESS"
    assert payload["route_id"] == "route-1"
    assert payload["correlation_id"] == "corr_logtest12345"
    assert "timestamp" in payload

    json.dumps(payload)
