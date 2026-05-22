"""Unit tests for upload complete service."""

import hashlib
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from models.complete import FileDescriptor, UploadCompleteRequest, ValidationStatus
from models.enums import TripLogStatus
from models.trip_log import TripLog
from services.blob_storage import BlobObjectProperties
from services.cosmos_db import TripLogNotFoundError
from services.upload_complete_service import TripOwnershipError, UploadCompleteService

_OWNER_USER_ID = "user-456"
_OTHER_USER_ID = "intruder-999"


def _trip_log() -> TripLog:
    return TripLog(
        id="sess_abc123",
        route_id="route-123",
        correlation_id="corr_xyz789",
        upload_session_id="sess_abc123",
        user_id=_OWNER_USER_ID,
        status=TripLogStatus.RECEIVED,
        created_at=datetime(2026, 5, 22, 12, 0, tzinfo=UTC),
        trip_storage_root="year=2026/month=05/day=22/",
        trip_file_prefix="20260522T120000Z_user-456_route-123",
    )


def _request(checksum: str = "abc123") -> UploadCompleteRequest:
    return UploadCompleteRequest(
        route_id="route-123",
        upload_session_id="sess_abc123",
        files=[
            FileDescriptor(name="gps.json", size=10, checksum=checksum),
        ],
    )


def _build_service(
    mock_blob: MagicMock,
    mock_cosmos: MagicMock,
    mock_event_hub: MagicMock,
    settings,
) -> UploadCompleteService:
    return UploadCompleteService(
        blob_service=mock_blob,
        cosmos_service=mock_cosmos,
        event_hub_service=mock_event_hub,
        settings=settings,
    )


def test_complete_upload_validates_and_publishes(settings) -> None:
    payload = b"0" * 10
    checksum = hashlib.md5(payload, usedforsecurity=False).hexdigest()

    mock_blob = MagicMock()
    mock_blob.blob_exists.return_value = True
    mock_blob.get_blob_properties.return_value = BlobObjectProperties(
        name="blob",
        size=10,
        content_md5=bytes.fromhex(checksum),
    )

    mock_cosmos = MagicMock()
    mock_cosmos.get_trip_log.return_value = (_trip_log(), "etag-0")
    mock_cosmos.update_trip_log.return_value = (_trip_log(), "etag-1")

    mock_event_hub = MagicMock()
    service = _build_service(mock_blob, mock_cosmos, mock_event_hub, settings)

    response = service.complete_upload(
        request=_request(checksum),
        correlation_id="corr-1",
        caller_user_id=_OWNER_USER_ID,
    )

    assert response.validation_status == ValidationStatus.VALIDATED
    mock_event_hub.publish_trip_event.assert_called_once()


def test_complete_upload_uses_deterministic_event_id(settings) -> None:
    """Event id must be derived from upload_session_id, not random."""
    payload = b"0" * 10
    checksum = hashlib.md5(payload, usedforsecurity=False).hexdigest()

    mock_blob = MagicMock()
    mock_blob.blob_exists.return_value = True
    mock_blob.get_blob_properties.return_value = BlobObjectProperties(
        name="blob", size=10, content_md5=bytes.fromhex(checksum)
    )

    mock_cosmos = MagicMock()
    mock_cosmos.get_trip_log.return_value = (_trip_log(), "etag-0")
    mock_cosmos.update_trip_log.return_value = (_trip_log(), "etag-1")

    mock_event_hub = MagicMock()
    service = _build_service(mock_blob, mock_cosmos, mock_event_hub, settings)

    service.complete_upload(
        request=_request(checksum),
        correlation_id="corr-1",
        caller_user_id=_OWNER_USER_ID,
    )
    service.complete_upload(
        request=_request(checksum),
        correlation_id="corr-2",
        caller_user_id=_OWNER_USER_ID,
    )

    calls = mock_event_hub.publish_trip_event.call_args_list
    event_id_1 = calls[0].args[0].event_id
    event_id_2 = calls[1].args[0].event_id
    assert event_id_1 == event_id_2 == "evt_sess_abc123"


def test_complete_upload_returns_idempotent_response_when_published(settings) -> None:
    published_log = _trip_log().model_copy(update={"status": TripLogStatus.PUBLISHED})
    mock_cosmos = MagicMock()
    mock_cosmos.get_trip_log.return_value = (published_log, "etag-0")

    service = _build_service(MagicMock(), mock_cosmos, MagicMock(), settings)
    response = service.complete_upload(
        request=_request(),
        correlation_id="corr-1",
        caller_user_id=_OWNER_USER_ID,
    )

    assert response.validation_status == ValidationStatus.VALIDATED
    assert len(response.files) == 4


def test_complete_upload_raises_when_trip_log_missing(settings) -> None:
    mock_cosmos = MagicMock()
    mock_cosmos.get_trip_log.return_value = (None, None)

    service = _build_service(MagicMock(), mock_cosmos, MagicMock(), settings)

    with pytest.raises(TripLogNotFoundError):
        service.complete_upload(
            request=_request(),
            correlation_id="corr-1",
            caller_user_id=_OWNER_USER_ID,
        )


def test_complete_upload_rejects_wrong_owner(settings) -> None:
    """A caller with a valid JWT but the wrong user_id must receive TripOwnershipError."""
    mock_cosmos = MagicMock()
    mock_cosmos.get_trip_log.return_value = (_trip_log(), "etag-0")

    service = _build_service(MagicMock(), mock_cosmos, MagicMock(), settings)

    with pytest.raises(TripOwnershipError):
        service.complete_upload(
            request=_request(),
            correlation_id="corr-1",
            caller_user_id=_OTHER_USER_ID,
        )
