"""End-to-end upload flow test using mocked Azure dependencies."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from api.v1.upload_complete import upload_complete
from api.v1.upload_session import upload_session
from models.enums import TripSource
from services.auth import create_mock_token


@pytest.mark.e2e
@patch("api.v1.upload_complete.UploadCompleteService")
@patch("api.v1.upload_session.UploadSessionService")
@patch("api.v1.upload_session.authenticate_request", return_value="user-test")
@patch("api.v1.upload_complete.authenticate_request", return_value="user-test")
def test_upload_flow_session_to_complete(
    _mock_complete_auth,
    _mock_session_auth,
    mock_session_service_cls,
    mock_complete_service_cls,
    http_request_factory,
    settings,
) -> None:
    token = create_mock_token("user-test", settings.jwt_mock_secret)
    auth_header = f"Bearer {token}"
    timestamp = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)

    from models.session import UploadSessionResponse, UploadTarget

    session_response = UploadSessionResponse(
        upload_session_id="sess_e2e123456",
        route_id="route-e2e",
        user_id="user-test",
        correlation_id="corr_e2e123456",
        expires_at=datetime(2026, 5, 22, 13, 0, tzinfo=UTC),
        uploads={
            TripSource.GPS: UploadTarget(
                source=TripSource.GPS,
                blob_path="source=gps/year=2026/month=05/day=22/file.json",
                sas_url="https://example?sas",
            ),
            TripSource.IMU: UploadTarget(
                source=TripSource.IMU,
                blob_path="source=imu/year=2026/month=05/day=22/file.bin",
                sas_url="https://example?sas",
            ),
            TripSource.BT: UploadTarget(
                source=TripSource.BT,
                blob_path="source=bt/year=2026/month=05/day=22/file.json",
                sas_url="https://example?sas",
            ),
            TripSource.METADATA: UploadTarget(
                source=TripSource.METADATA,
                blob_path="source=metadata/year=2026/month=05/day=22/file.json",
                sas_url="https://example?sas",
            ),
        },
    )
    mock_session_service_cls.return_value.create_session.return_value = session_response

    session_http = upload_session(
        http_request_factory(
            method="POST",
            url="/api/upload/session",
            headers={"Authorization": auth_header, "x-correlation-id": "corr_e2e123456"},
            body=b'{"route_id":"route-e2e"}',
        ),
    )
    assert session_http.status_code == 201
    session_body = json.loads(session_http.get_body())
    assert session_body["upload_session_id"] == "sess_e2e123456"

    from models.complete import CompleteResponse, FileValidationResult, FileValidationStatus, ValidationStatus

    complete_response = CompleteResponse(
        route_id="route-e2e",
        upload_session_id="sess_e2e123456",
        correlation_id="corr_e2e123456",
        validation_status=ValidationStatus.VALIDATED,
        files=[
            FileValidationResult(name="gps.json", status=FileValidationStatus.VALID),
        ],
    )
    mock_complete_service_cls.return_value.complete_upload.return_value = complete_response

    payload = b"0" * 10
    checksum = hashlib.md5(payload, usedforsecurity=False).hexdigest()
    complete_http = upload_complete(
        http_request_factory(
            method="POST",
            url="/api/upload/complete",
            headers={"Authorization": auth_header, "x-correlation-id": "corr_e2e123456"},
            body=json.dumps(
                {
                    "route_id": "route-e2e",
                    "upload_session_id": "sess_e2e123456",
                    "files": [{"name": "gps.json", "size": 10, "checksum": checksum}],
                },
            ).encode(),
        ),
    )
    assert complete_http.status_code == 200
    complete_body = json.loads(complete_http.get_body())
    assert complete_body["validation_status"] == "VALIDATED"
