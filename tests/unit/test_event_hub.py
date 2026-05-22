"""Unit tests for EventHubService."""

import json
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest

from models.enums import TripSource
from models.trip_event import TripEvent
from services.event_hub import EventHubConfigurationError, EventHubService


def _sample_trip_event() -> TripEvent:
    return TripEvent(
        event_id="evt_98765",
        correlation_id="corr_abc123",
        trip_id="98765",
        route_id="aaa-4567",
        user_id="123",
        upload_session_id="sess_9f2a1c",
        trip_date=date(2026, 5, 19),
        uploaded_at=datetime(2026, 5, 19, 10, 30, tzinfo=UTC),
        available_sources=[TripSource.GPS, TripSource.IMU, TripSource.BT],
        trip_storage_root="year=2026/month=05/day=19/",
        trip_file_prefix="20260519T103000Z_123_aaa-4567",
    )


def test_serialize_trip_event_returns_json(settings) -> None:
    service = EventHubService(settings=settings)
    payload = service.serialize_trip_event(_sample_trip_event())
    parsed = json.loads(payload)

    assert parsed["event_id"] == "evt_98765"
    assert parsed["available_sources"] == ["gps", "imu", "bt"]
    assert parsed["trip_date"] == "2026-05-19"


def test_publish_trip_event_sends_batch(settings) -> None:
    mock_batch = MagicMock()
    mock_producer = MagicMock()
    mock_producer.create_batch.return_value = mock_batch

    service = EventHubService(settings=settings, producer=mock_producer)
    trip_event = _sample_trip_event()
    service.publish_trip_event(trip_event)

    mock_producer.create_batch.assert_called_once_with(partition_key="aaa-4567")
    mock_batch.add.assert_called_once()
    mock_producer.send_batch.assert_called_once_with(mock_batch)

    sent_event = mock_batch.add.call_args.args[0]
    assert json.loads(sent_event.body_as_str(encoding="utf-8"))["event_id"] == "evt_98765"
    assert sent_event.properties["correlation_id"] == "corr_abc123"


def test_publish_trip_event_requires_namespace(settings) -> None:
    settings.eventhub_fully_qualified_namespace = ""
    service = EventHubService(settings=settings)

    with pytest.raises(EventHubConfigurationError):
        service.publish_trip_event(_sample_trip_event())
