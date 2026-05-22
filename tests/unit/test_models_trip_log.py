"""Unit tests for trip log models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from models.enums import TripLogStatus
from models.trip_log import TripLog


def test_trip_log_accepts_received_status() -> None:
    trip_log = TripLog(
        id="sess_abc123",
        route_id="route-123",
        correlation_id="corr_xyz789",
        upload_session_id="sess_abc123",
        user_id="user-456",
        status=TripLogStatus.RECEIVED,
        created_at=datetime(2026, 5, 22, 12, 0, tzinfo=UTC),
    )

    assert trip_log.status == TripLogStatus.RECEIVED
    assert trip_log.gps_exists is False


def test_trip_log_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        TripLog(
            id="sess_abc123",
            route_id="route-123",
            correlation_id="corr_xyz789",
            upload_session_id="sess_abc123",
            user_id="user-456",
            status="UNKNOWN",
            created_at=datetime(2026, 5, 22, 12, 0, tzinfo=UTC),
        )
