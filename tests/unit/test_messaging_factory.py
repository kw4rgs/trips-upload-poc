"""Unit tests for the messaging factory."""

from unittest.mock import patch

import pytest

from services.messaging_factory import get_publisher
from services.event_hub import EventHubPublisher
from shared.messaging import TripEventPublisher


def test_get_publisher_returns_event_hub_publisher_in_production(settings) -> None:
    settings.environment = "production"
    publisher = get_publisher(settings)
    assert isinstance(publisher, EventHubPublisher)
    assert isinstance(publisher, TripEventPublisher)


def test_get_publisher_returns_kafka_publisher_in_local(settings) -> None:
    settings.environment = "local"
    publisher = get_publisher(settings)
    # Import lazily to avoid requiring a running broker in tests
    from services.kafka_publisher import KafkaPublisher
    assert isinstance(publisher, KafkaPublisher)
    assert isinstance(publisher, TripEventPublisher)


def test_get_publisher_uses_cached_settings_when_none_provided(settings) -> None:
    with patch("services.messaging_factory.get_settings", return_value=settings):
        settings.environment = "production"
        publisher = get_publisher()
        assert isinstance(publisher, EventHubPublisher)
