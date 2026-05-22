"""Unit tests for CosmosService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

from models.enums import TripLogStatus
from models.trip_log import TripLog
from services.cosmos_db import CosmosConflictError, CosmosService, TripLogNotFoundError


def _sample_trip_log() -> TripLog:
    return TripLog(
        id="sess_abc123",
        route_id="route-123",
        correlation_id="corr_xyz789",
        upload_session_id="sess_abc123",
        user_id="user-456",
        status=TripLogStatus.RECEIVED,
        created_at=datetime(2026, 5, 22, 12, 0, tzinfo=UTC),
    )


def _item(trip_log: TripLog, etag: str = "etag-abc") -> dict:
    """Simulate a raw Cosmos item dict (includes SDK metadata fields)."""
    doc = trip_log.model_dump(mode="json")
    doc["_etag"] = etag
    doc["_ts"] = 1234567890
    return doc


def test_create_trip_log_persists_document(settings) -> None:
    trip_log = _sample_trip_log()
    mock_container = MagicMock()
    mock_container.create_item.return_value = _item(trip_log)

    service = CosmosService(settings=settings, container=mock_container)
    created = service.create_trip_log(trip_log)

    assert created.upload_session_id == "sess_abc123"
    mock_container.create_item.assert_called_once()


def test_create_trip_log_requires_matching_ids(settings) -> None:
    trip_log = _sample_trip_log().model_copy(update={"id": "different"})
    service = CosmosService(settings=settings, container=MagicMock())

    with pytest.raises(ValueError, match="must match upload_session_id"):
        service.create_trip_log(trip_log)


def test_get_trip_log_returns_none_when_missing(settings) -> None:
    mock_container = MagicMock()
    mock_container.read_item.side_effect = CosmosResourceNotFoundError()

    service = CosmosService(settings=settings, container=mock_container)
    trip_log, etag = service.get_trip_log("route-123", "sess_missing")
    assert trip_log is None
    assert etag is None


def test_get_trip_log_returns_etag(settings) -> None:
    trip_log = _sample_trip_log()
    mock_container = MagicMock()
    mock_container.read_item.return_value = _item(trip_log, etag="etag-xyz")

    service = CosmosService(settings=settings, container=mock_container)
    result, etag = service.get_trip_log("route-123", "sess_abc123")

    assert result is not None
    assert etag == "etag-xyz"


def test_trip_exists(settings) -> None:
    trip_log = _sample_trip_log()
    mock_container = MagicMock()
    mock_container.read_item.return_value = _item(trip_log)

    service = CosmosService(settings=settings, container=mock_container)
    assert service.trip_exists("route-123", "sess_abc123") is True


def test_update_trip_log_changes_status(settings) -> None:
    trip_log = _sample_trip_log()
    mock_container = MagicMock()
    mock_container.read_item.return_value = _item(trip_log)
    updated_log = trip_log.model_copy(update={"status": TripLogStatus.VALIDATED})
    mock_container.replace_item.return_value = _item(updated_log, etag="etag-new")

    service = CosmosService(settings=settings, container=mock_container)
    result, new_etag = service.update_trip_log(
        "route-123",
        "sess_abc123",
        status=TripLogStatus.VALIDATED,
    )

    assert result.status == TripLogStatus.VALIDATED
    assert new_etag == "etag-new"
    mock_container.replace_item.assert_called_once()


def test_update_trip_log_uses_caller_etag_for_if_match(settings) -> None:
    """Caller's etag must be forwarded to replace_item as if_match."""
    trip_log = _sample_trip_log()
    mock_container = MagicMock()
    mock_container.read_item.return_value = _item(trip_log, etag="etag-current")
    mock_container.replace_item.return_value = _item(trip_log, etag="etag-new")

    service = CosmosService(settings=settings, container=mock_container)
    service.update_trip_log(
        "route-123",
        "sess_abc123",
        etag="etag-original",
        status=TripLogStatus.VALIDATING,
    )

    call_kwargs = mock_container.replace_item.call_args.kwargs
    assert call_kwargs.get("if_match") == "etag-original"


def test_update_trip_log_raises_conflict_on_412(settings) -> None:
    trip_log = _sample_trip_log()
    mock_container = MagicMock()
    mock_container.read_item.return_value = _item(trip_log)

    conflict_error = CosmosHttpResponseError()
    conflict_error.status_code = 412
    mock_container.replace_item.side_effect = conflict_error

    service = CosmosService(settings=settings, container=mock_container)
    with pytest.raises(CosmosConflictError):
        service.update_trip_log(
            "route-123",
            "sess_abc123",
            etag="stale-etag",
            status=TripLogStatus.VALIDATING,
        )


def test_update_trip_log_raises_when_missing(settings) -> None:
    mock_container = MagicMock()
    mock_container.read_item.side_effect = CosmosResourceNotFoundError()
    service = CosmosService(settings=settings, container=mock_container)

    with pytest.raises(TripLogNotFoundError):
        service.update_trip_log("route-123", "sess_missing", status=TripLogStatus.FAILED)


def test_new_trip_log_factory(settings) -> None:
    service = CosmosService(settings=settings, container=MagicMock())
    trip_log = service.new_trip_log(
        route_id="route-123",
        upload_session_id="sess_new123",
        user_id="user-1",
        correlation_id="corr_new123",
    )

    assert trip_log.id == "sess_new123"
    assert trip_log.status == TripLogStatus.RECEIVED
