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
from services.upload_complete_service import UploadCompleteService


def _trip_log() -> TripLog:
    return TripLog(
        id="sess_abc123",
        route_id="route-123",
        correlation_id="corr_xyz789",
        upload_session_id="sess_abc123",
        user_id="user-456",
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
    mock_cosmos.get_trip_log.return_value = _trip_log()

    mock_event_hub = MagicMock()
    service = UploadCompleteService(
        blob_service=mock_blob,
        cosmos_service=mock_cosmos,
        event_hub_service=mock_event_hub,
        settings=settings,
    )

    response = service.complete_upload(request=_request(checksum), correlation_id="corr-1")

    assert response.validation_status == ValidationStatus.VALIDATED
    mock_event_hub.publish_trip_event.assert_called_once()


def test_complete_upload_returns_idempotent_response_when_published(settings) -> None:
    published_log = _trip_log().model_copy(update={"status": TripLogStatus.PUBLISHED})
    mock_cosmos = MagicMock()
    mock_cosmos.get_trip_log.return_value = published_log

    service = UploadCompleteService(
        blob_service=MagicMock(),
        cosmos_service=mock_cosmos,
        event_hub_service=MagicMock(),
        settings=settings,
    )
    response = service.complete_upload(request=_request(), correlation_id="corr-1")

    assert response.validation_status == ValidationStatus.VALIDATED
    assert len(response.files) == 4


def test_complete_upload_raises_when_trip_log_missing(settings) -> None:
    mock_cosmos = MagicMock()
    mock_cosmos.get_trip_log.return_value = None
    service = UploadCompleteService(
        blob_service=MagicMock(),
        cosmos_service=mock_cosmos,
        event_hub_service=MagicMock(),
        settings=settings,
    )

    with pytest.raises(TripLogNotFoundError):
        service.complete_upload(request=_request(), correlation_id="corr-1")
