"""Unit tests for upload session models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from models.enums import TripSource
from models.session import UploadSessionRequest, UploadSessionResponse, UploadTarget


def test_upload_session_request_accepts_route_id() -> None:
    request = UploadSessionRequest(route_id="route-123")
    assert request.route_id == "route-123"


def test_upload_session_request_rejects_empty_route_id() -> None:
    with pytest.raises(ValidationError):
        UploadSessionRequest(route_id="")


def test_upload_session_response_requires_all_sources() -> None:
    expires_at = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)
    uploads = {
        TripSource.GPS: UploadTarget(
            source=TripSource.GPS,
            blob_path="landing/source=gps/year=2026/month=05/day=22/file.json",
            sas_url="https://example.blob.core.windows.net/landing/gps?sas",
        ),
        TripSource.IMU: UploadTarget(
            source=TripSource.IMU,
            blob_path="landing/source=imu/year=2026/month=05/day=22/file.bin",
            sas_url="https://example.blob.core.windows.net/landing/imu?sas",
        ),
        TripSource.BT: UploadTarget(
            source=TripSource.BT,
            blob_path="landing/source=bt/year=2026/month=05/day=22/file.json",
            sas_url="https://example.blob.core.windows.net/landing/bt?sas",
        ),
        TripSource.METADATA: UploadTarget(
            source=TripSource.METADATA,
            blob_path="landing/source=metadata/year=2026/month=05/day=22/file.json",
            sas_url="https://example.blob.core.windows.net/landing/metadata?sas",
        ),
    }

    response = UploadSessionResponse(
        upload_session_id="sess_abc123",
        route_id="route-123",
        user_id="user-456",
        correlation_id="corr_xyz789",
        expires_at=expires_at,
        uploads=uploads,
    )

    assert len(response.uploads) == 4
    assert response.uploads[TripSource.GPS].source == TripSource.GPS


def test_upload_session_response_rejects_missing_source() -> None:
    with pytest.raises(ValidationError, match="missing upload targets"):
        UploadSessionResponse(
            upload_session_id="sess_abc123",
            route_id="route-123",
            user_id="user-456",
            correlation_id="corr_xyz789",
            expires_at=datetime(2026, 5, 22, 12, 0, tzinfo=UTC),
            uploads={
                TripSource.GPS: UploadTarget(
                    source=TripSource.GPS,
                    blob_path="path",
                    sas_url="https://example?sas",
                ),
            },
        )
