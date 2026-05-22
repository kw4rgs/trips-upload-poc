"""Kafka publisher — local development messaging backend.

Publishes trip metadata events to a Kafka-compatible broker (tested with
Redpanda running in Docker via ``docker-compose``).

In production use ``EventHubPublisher`` instead.
The active implementation is selected by ``services/messaging_factory.get_publisher()``.
"""

from __future__ import annotations

from kafka import KafkaProducer
from kafka.errors import KafkaError

from config import Settings, get_settings
from models.trip_event import TripEvent


class KafkaPublisherError(Exception):
    """Base Kafka publisher error."""


class KafkaPublisherConfigurationError(KafkaPublisherError):
    """Kafka publisher is misconfigured."""


class KafkaPublisher:
    """Kafka producer for trip metadata events (local development).

    Connects to the broker specified by ``KAFKA_BOOTSTRAP_SERVERS`` and
    publishes JSON-serialized ``TripEvent`` messages to ``KAFKA_TOPIC``.

    The ``KafkaProducer`` is initialised lazily on the first
    ``publish_trip_event`` call and reused for the lifetime of the process,
    matching the same lifecycle pattern as ``EventHubPublisher``.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        producer: KafkaProducer | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._producer = producer

    def _create_producer(self) -> KafkaProducer:
        bootstrap_servers = self._settings.kafka_bootstrap_servers
        if not bootstrap_servers:
            raise KafkaPublisherConfigurationError(
                "KAFKA_BOOTSTRAP_SERVERS is not configured",
            )

        return KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            # Serialise message values as UTF-8 encoded JSON strings.
            value_serializer=lambda payload: payload.encode("utf-8"),
            # Include routing metadata in message headers.
            client_id="trips-upload-poc",
            acks="all",
            retries=3,
        )

    def publish_trip_event(self, trip_event: TripEvent) -> None:
        """Publish a trip event to the configured Kafka topic.

        Blocks until the broker acknowledges the message (``acks='all'``).

        Args:
            trip_event: Validated trip metadata event to publish.

        Raises:
            KafkaPublisherError: On broker communication failure.
        """
        if self._producer is None:
            self._producer = self._create_producer()

        payload = trip_event.model_dump_json()
        headers = [
            ("event_id", trip_event.event_id.encode()),
            ("route_id", trip_event.route_id.encode()),
            ("correlation_id", trip_event.correlation_id.encode()),
        ]

        try:
            future = self._producer.send(
                self._settings.kafka_topic,
                value=payload,
                key=trip_event.route_id.encode(),
                headers=headers,
            )
            # Block until broker confirms receipt.
            self._producer.flush()
            future.get(timeout=10)
        except KafkaError as exc:
            raise KafkaPublisherError(
                f"Failed to publish trip event {trip_event.event_id}: {exc}",
            ) from exc

    def close(self) -> None:
        """Flush pending messages and close the producer connection."""
        if self._producer is not None:
            self._producer.flush()
            self._producer.close()
            self._producer = None
