"""Unit tests for HTTP error responses on upload endpoints."""

import json
from unittest.mock import MagicMock, patch

from models.complete import CompleteResponse, FileValidationResult, FileValidationStatus, ValidationStatus
from services.cosmos_db import CosmosDbError

from api.v1.upload_complete import upload_complete
from api.v1.upload_session import upload_session


@patch("api.v1.upload_session.UploadSessionService")
@patch("api.v1.upload_session.authenticate_request", return_value="user-1")
def test_upload_session_error_response_shape(
    _mock_auth,
    mock_service_cls,
    http_request_factory,
    auth_token,
) -> None:
    mock_service = MagicMock()
    mock_service.create_session.side_effect = CosmosDbError("cosmos unavailable")
    mock_service_cls.return_value = mock_service

    response = upload_session(
        http_request_factory(
            method="POST",
            url="/api/upload/session",
            headers={"Authorization": auth_token, "x-correlation-id": "corr_err001"},
            body=b'{"route_id":"route-1"}',
        ),
    )

    assert response.status_code == 503
    body = json.loads(response.get_body())
    assert body["error"] == "service_unavailable"


@patch("api.v1.upload_complete.UploadCompleteService")
@patch("api.v1.upload_complete.authenticate_request", return_value="user-1")
def test_upload_complete_returns_404_error_shape(
    _mock_auth,
    mock_service_cls,
    http_request_factory,
    auth_token,
) -> None:
    from services.cosmos_db import TripLogNotFoundError

    mock_service = MagicMock()
    mock_service.complete_upload.side_effect = TripLogNotFoundError("missing")
    mock_service_cls.return_value = mock_service

    response = upload_complete(
        http_request_factory(
            method="POST",
            url="/api/upload/complete",
            headers={"Authorization": auth_token, "x-correlation-id": "corr_err002"},
            body=b'{"route_id":"route-1","upload_session_id":"sess_x","files":[{"name":"gps.json","size":1,"checksum":"ab"}]}',
        ),
    )

    assert response.status_code == 404
    body = json.loads(response.get_body())
    assert body["error"] == "not_found"
    assert body["correlation_id"] == "corr_err002"


@patch("api.v1.upload_complete.UploadCompleteService")
@patch("api.v1.upload_complete.authenticate_request", return_value="user-1")
def test_upload_complete_returns_409_on_validation_failed(
    _mock_auth,
    mock_service_cls,
    http_request_factory,
    auth_token,
) -> None:
    mock_service = MagicMock()
    mock_service.complete_upload.return_value = CompleteResponse(
        route_id="route-1",
        upload_session_id="sess_x",
        correlation_id="corr-1",
        validation_status=ValidationStatus.FAILED,
        files=[
            FileValidationResult(
                name="gps.json",
                status=FileValidationStatus.FAILED,
                error="checksum mismatch",
            ),
        ],
    )
    mock_service_cls.return_value = mock_service

    response = upload_complete(
        http_request_factory(
            method="POST",
            url="/api/upload/complete",
            headers={"Authorization": auth_token},
            body=b'{"route_id":"route-1","upload_session_id":"sess_x","files":[{"name":"gps.json","size":1,"checksum":"ab"}]}',
        ),
    )

    assert response.status_code == 409
