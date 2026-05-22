"""Messaging backend factory.

Returns the correct ``TripEventPublisher`` implementation based on the
``ENVIRONMENT`` setting:

- ``local``      → ``KafkaPublisher``  (Redpanda / local Kafka via docker-compose)
- ``production`` → ``EventHubPublisher`` (Azure Event Hubs with Managed Identity)

Usage::

    from services.messaging_factory import get_publisher

    publisher = get_publisher()          # uses cached Settings
    publisher.publish_trip_event(event)
"""

from __future__ import annotations

from config import Settings, get_settings
from shared.messaging import TripEventPublisher


def get_publisher(settings: Settings | None = None) -> TripEventPublisher:
    """Return the active messaging publisher for the current environment.

    Imports are deferred so that the Kafka SDK is only loaded when actually
    running in local mode, avoiding import errors when ``kafka-python`` is not
    installed in production containers.

    Args:
        settings: Optional pre-built ``Settings`` instance; defaults to the
            cached singleton from ``get_settings()``.

    Returns:
        A ``TripEventPublisher``-compatible object.
    """
    resolved = settings or get_settings()

    if resolved.environment == "local":
        from services.kafka_publisher import KafkaPublisher

        return KafkaPublisher(resolved)

    from services.event_hub import EventHubPublisher

    return EventHubPublisher(resolved)
