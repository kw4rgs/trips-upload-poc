"""Unit tests for upload session service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from models.enums import TripLogStatus, TripSource
from models.trip_log import TripLog
from services.blob_storage import GeneratedSas
from services.upload_session_service import UploadSessionService


def test_create_session_returns_sas_for_all_sources(settings) -> None:
    mock_blob = MagicMock()
    mock_blob.generate_sas.return_value = GeneratedSas(
        blob_path="source=gps/year=2026/month=05/day=22/file.json",
        sas_url="https://example.blob.core.windows.net/landing/file?sas",
        expires_at=datetime(2026, 5, 22, 13, 0, tzinfo=UTC),
    )
    mock_blob.build_upload_target_path.side_effect = (
        lambda source, user_id, route_id, timestamp: f"path/{source.value}"
    )

    mock_cosmos = MagicMock()
    mock_cosmos.new_trip_log.return_value = TripLog(
        id="sess_test123456",
        route_id="route-1",
        correlation_id="corr-1",
        upload_session_id="sess_test123456",
        user_id="user-1",
        status=TripLogStatus.RECEIVED,
        created_at=datetime(2026, 5, 22, 12, 0, tzinfo=UTC),
    )

    service = UploadSessionService(
        blob_service=mock_blob,
        cosmos_service=mock_cosmos,
        settings=settings,
    )
    response = service.create_session(
        route_id="route-1",
        user_id="user-1",
        correlation_id="corr-1",
    )

    assert response.route_id == "route-1"
    assert len(response.uploads) == len(TripSource)
    assert response.uploads[TripSource.GPS].sas_url.startswith("https://")
    mock_cosmos.create_trip_log.assert_called_once()
