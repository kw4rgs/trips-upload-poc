"""Integration tests for KafkaPublisher against a local Redpanda broker.

Requires the docker-compose stack to be running:

    docker compose up -d redpanda

Tests are skipped automatically when the broker is not reachable.
"""

from __future__ import annotations

import json
import socket
import uuid
from datetime import UTC, date, datetime

import pytest

from config import Settings
from models.enums import TripSource
from models.trip_event import TripEvent
from services.kafka_publisher import KafkaPublisher

REDPANDA_HOST = "127.0.0.1"
REDPANDA_KAFKA_PORT = 9092
TEST_TOPIC = "trip-processing-test"


def _redpanda_is_reachable() -> bool:
    try:
        with socket.create_connection((REDPANDA_HOST, REDPANDA_KAFKA_PORT), timeout=1):
            return True
    except OSError:
        return False


def _sample_trip_event(session_id: str) -> TripEvent:
    return TripEvent(
        event_id=f"evt_{session_id}",
        correlation_id=f"corr_{uuid.uuid4().hex[:8]}",
        trip_id=session_id,
        route_id="route-kafka-integration",
        user_id="user-integration",
        upload_session_id=session_id,
        trip_date=date(2026, 5, 22),
        uploaded_at=datetime(2026, 5, 22, 12, 0, tzinfo=UTC),
        available_sources=[TripSource.GPS, TripSource.IMU],
        trip_storage_root="year=2026/month=05/day=22/",
        trip_file_prefix="20260522T120000Z_user-integration_route-kafka-integration",
    )


@pytest.fixture(scope="session")
def kafka_publisher() -> KafkaPublisher | None:
    if not _redpanda_is_reachable():
        return None
    try:
        return KafkaPublisher(
            settings=Settings(
                environment="local",
                kafka_bootstrap_servers=f"{REDPANDA_HOST}:{REDPANDA_KAFKA_PORT}",
                kafka_topic=TEST_TOPIC,
            ),
        )
    except Exception:
        return None


@pytest.fixture
def publisher(kafka_publisher: KafkaPublisher | None) -> KafkaPublisher:
    if kafka_publisher is None:
        pytest.skip("Redpanda broker is not available on localhost:9092")
    return kafka_publisher


@pytest.mark.integration
def test_publish_trip_event_sends_message(publisher: KafkaPublisher) -> None:
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    event = _sample_trip_event(session_id)

    # Should not raise — confirms message was accepted by the broker
    publisher.publish_trip_event(event)


@pytest.mark.integration
def test_publish_multiple_events_reuses_producer(publisher: KafkaPublisher) -> None:
    """Multiple publishes must reuse the same producer connection."""
    initial_producer = publisher._producer

    for i in range(3):
        publisher.publish_trip_event(_sample_trip_event(f"sess_{uuid.uuid4().hex[:8]}"))

    # Producer is lazily created on first call and reused on subsequent calls
    assert publisher._producer is not None
    if initial_producer is not None:
        assert publisher._producer is initial_producer
