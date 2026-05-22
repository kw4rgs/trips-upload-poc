"""Unit tests for Event Hub trip event models."""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from models.enums import TripSource
from models.trip_event import TripEvent


def test_trip_event_accepts_metadata_payload() -> None:
    event = TripEvent(
        event_id="evt_98765",
        correlation_id="corr_abc123",
        trip_id="98765",
        route_id="aaa-4567",
        user_id="123",
        upload_session_id="sess_9f2a1c",
        trip_date=date(2026, 5, 19),
        uploaded_at=datetime(2026, 5, 19, 10, 30, tzinfo=UTC),
        available_sources=[TripSource.GPS, TripSource.IMU, TripSource.BT],
        trip_storage_root="landing/year=2026/month=05/day=05/",
        trip_file_prefix="20260505T121314Z_123_aaa-4567",
    )

    payload = event.model_dump(mode="json")
    assert payload["available_sources"] == ["gps", "imu", "bt"]
    assert payload["trip_date"] == "2026-05-19"


def test_trip_event_rejects_duplicate_sources() -> None:
    with pytest.raises(ValidationError, match="duplicates"):
        TripEvent(
            event_id="evt_98765",
            correlation_id="corr_abc123",
            trip_id="98765",
            route_id="aaa-4567",
            user_id="123",
            upload_session_id="sess_9f2a1c",
            trip_date=date(2026, 5, 19),
            uploaded_at=datetime(2026, 5, 19, 10, 30, tzinfo=UTC),
            available_sources=[TripSource.GPS, TripSource.GPS],
            trip_storage_root="landing/year=2026/month=05/day=05/",
            trip_file_prefix="20260505T121314Z_123_aaa-4567",
        )
