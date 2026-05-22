"""Unit tests for upload session HTTP endpoint."""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from models.enums import TripSource
from models.session import UploadSessionResponse, UploadTarget

from api.v1.upload_session import upload_session


def test_upload_session_returns_401_without_auth(http_request_factory) -> None:
    response = upload_session(
        http_request_factory(
            method="POST",
            url="/api/upload/session",
            body=b'{"route_id":"route-1"}',
        ),
    )
    assert response.status_code == 401


@patch("api.v1.upload_session.UploadSessionService")
@patch("api.v1.upload_session.authenticate_request", return_value="user-1")
def test_upload_session_returns_201(
    _mock_auth,
    mock_service_cls,
    http_request_factory,
    auth_token,
) -> None:
    mock_service = MagicMock()
    mock_service.create_session.return_value = UploadSessionResponse(
        upload_session_id="sess_test123456",
        route_id="route-1",
        user_id="user-1",
        correlation_id="corr-1",
        expires_at=datetime(2026, 5, 22, 13, 0, tzinfo=UTC),
        uploads={
            TripSource.GPS: UploadTarget(
                source=TripSource.GPS,
                blob_path="path/gps",
                sas_url="https://example?sas",
            ),
            TripSource.IMU: UploadTarget(
                source=TripSource.IMU,
                blob_path="path/imu",
                sas_url="https://example?sas",
            ),
            TripSource.BT: UploadTarget(
                source=TripSource.BT,
                blob_path="path/bt",
                sas_url="https://example?sas",
            ),
            TripSource.METADATA: UploadTarget(
                source=TripSource.METADATA,
                blob_path="path/metadata",
                sas_url="https://example?sas",
            ),
        },
    )
    mock_service_cls.return_value = mock_service

    response = upload_session(
        http_request_factory(
            method="POST",
            url="/api/upload/session",
            headers={"Authorization": auth_token},
            body=b'{"route_id":"route-1"}',
        ),
    )

    assert response.status_code == 201
    body = json.loads(response.get_body())
    assert body["upload_session_id"] == "sess_test123456"
