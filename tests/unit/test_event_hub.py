"""Unit tests for EventHubPublisher."""

import json
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest

from models.enums import TripSource
from models.trip_event import TripEvent
from services.event_hub import EventHubConfigurationError, EventHubPublisher
from shared.messaging import TripEventPublisher


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


def test_event_hub_publisher_satisfies_protocol() -> None:
    assert isinstance(EventHubPublisher, type)
    assert issubclass(EventHubPublisher, object)
    mock_producer = MagicMock()
    publisher = EventHubPublisher(producer=mock_producer)
    assert isinstance(publisher, TripEventPublisher)


def test_serialize_trip_event_returns_json(settings) -> None:
    publisher = EventHubPublisher(settings=settings)
    payload = publisher.serialize_trip_event(_sample_trip_event())
    parsed = json.loads(payload)

    assert parsed["event_id"] == "evt_98765"
    assert parsed["available_sources"] == ["gps", "imu", "bt"]
    assert parsed["trip_date"] == "2026-05-19"


def test_publish_trip_event_sends_batch(settings) -> None:
    mock_batch = MagicMock()
    mock_producer = MagicMock()
    mock_producer.create_batch.return_value = mock_batch

    publisher = EventHubPublisher(settings=settings, producer=mock_producer)
    trip_event = _sample_trip_event()
    publisher.publish_trip_event(trip_event)

    mock_producer.create_batch.assert_called_once_with(partition_key="aaa-4567")
    mock_batch.add.assert_called_once()
    mock_producer.send_batch.assert_called_once_with(mock_batch)

    sent_event = mock_batch.add.call_args.args[0]
    assert json.loads(sent_event.body_as_str(encoding="utf-8"))["event_id"] == "evt_98765"
    assert sent_event.properties["correlation_id"] == "corr_abc123"


def test_publish_reuses_producer_across_calls(settings) -> None:
    """Producer must be created once and reused (FX-07)."""
    mock_batch = MagicMock()
    mock_producer = MagicMock()
    mock_producer.create_batch.return_value = mock_batch

    publisher = EventHubPublisher(settings=settings)
    publisher._producer = mock_producer  # inject after construction

    publisher.publish_trip_event(_sample_trip_event())
    publisher.publish_trip_event(_sample_trip_event())

    # _create_producer is never called because _producer is already set
    assert mock_producer.create_batch.call_count == 2
    assert mock_producer.send_batch.call_count == 2


def test_publish_trip_event_requires_namespace(settings) -> None:
    settings.eventhub_fully_qualified_namespace = ""
    publisher = EventHubPublisher(settings=settings)

    with pytest.raises(EventHubConfigurationError):
        publisher.publish_trip_event(_sample_trip_event())
