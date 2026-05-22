"""Event Hub publisher — production messaging backend.

Uses the Azure Event Hubs AMQP SDK with Managed Identity (DefaultAzureCredential).
For local development use ``KafkaPublisher`` instead (see ``services/kafka_publisher.py``).
The active implementation is selected by ``services/messaging_factory.get_publisher()``.
"""

from __future__ import annotations

from typing import Any

from azure.eventhub import EventData, EventHubProducerClient
from azure.identity import DefaultAzureCredential

from config import Settings, get_settings
from models.trip_event import TripEvent


class EventHubError(Exception):
    """Base Event Hub error."""


class EventHubConfigurationError(EventHubError):
    """Event Hub service is misconfigured."""


class EventHubPublisher:
    """Azure Event Hub publisher for trip metadata events (production).

    The underlying ``EventHubProducerClient`` is initialised lazily on the
    first ``publish_trip_event`` call and reused for the lifetime of the
    worker process — avoiding a new AMQP connection on every HTTP request.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        producer: EventHubProducerClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._producer = producer

    def _create_producer(self) -> EventHubProducerClient:
        namespace = self._settings.eventhub_fully_qualified_namespace
        if not namespace:
            raise EventHubConfigurationError(
                "EVENTHUB_FULLY_QUALIFIED_NAMESPACE is not configured",
            )

        return EventHubProducerClient(
            fully_qualified_namespace=namespace,
            eventhub_name=self._settings.eventhub_name,
            credential=DefaultAzureCredential(),
        )

    def serialize_trip_event(self, trip_event: TripEvent) -> str:
        """Serialize a trip event to JSON for Event Hub."""
        return trip_event.model_dump_json()

    def publish_trip_event(self, trip_event: TripEvent) -> None:
        """Publish a metadata-only trip event to Event Hub.

        The producer client is created on first call and reused on subsequent
        calls within the same worker process (FX-07).
        """
        if self._producer is None:
            self._producer = self._create_producer()

        payload = self.serialize_trip_event(trip_event)
        event = EventData(body=payload)
        event.properties = self._build_event_properties(trip_event)

        batch = self._producer.create_batch(partition_key=trip_event.route_id)
        batch.add(event)
        self._producer.send_batch(batch)

    @staticmethod
    def _build_event_properties(trip_event: TripEvent) -> dict[str, Any]:
        return {
            "correlation_id": trip_event.correlation_id,
            "route_id": trip_event.route_id,
            "upload_session_id": trip_event.upload_session_id,
            "event_id": trip_event.event_id,
        }


# Backward-compatible alias — remove once all callers migrate to EventHubPublisher.
EventHubService = EventHubPublisher
