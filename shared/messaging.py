"""Messaging abstraction — TripEventPublisher Protocol.

Any class that implements ``publish_trip_event`` satisfies this Protocol and
can be injected into ``UploadCompleteService`` without modification.  Two
concrete implementations exist:

- ``EventHubPublisher`` (``services/event_hub.py``) — production path using
  the Azure Event Hubs AMQP SDK with Managed Identity.
- ``KafkaPublisher`` (``services/kafka_publisher.py``) — local development
  path backed by any Kafka-compatible broker (e.g. Redpanda in Docker).

The active implementation is selected by ``services/messaging_factory.py``
based on the ``ENVIRONMENT`` environment variable.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from models.trip_event import TripEvent


@runtime_checkable
class TripEventPublisher(Protocol):
    """Structural interface for publishing trip metadata events."""

    def publish_trip_event(self, trip_event: TripEvent) -> None:
        """Publish a single trip event to the configured messaging backend.

        Args:
            trip_event: Validated trip metadata event to publish.

        Raises:
            Any backend-specific exception on failure.
        """
        ...
