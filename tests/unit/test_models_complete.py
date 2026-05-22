"""Unit tests for upload complete models."""

import pytest
from pydantic import ValidationError

from models.complete import (
    CompleteResponse,
    FileDescriptor,
    FileValidationResult,
    FileValidationStatus,
    UploadCompleteRequest,
    ValidationStatus,
)


def _file(name: str, size: int = 100, checksum: str = "abc123") -> FileDescriptor:
    return FileDescriptor(name=name, size=size, checksum=checksum)


def test_upload_complete_request_accepts_valid_payload() -> None:
    request = UploadCompleteRequest(
        route_id="route-123",
        upload_session_id="sess_abc123",
        files=[
            _file("gps.json"),
            _file("imu.bin"),
            _file("bt.json"),
            _file("metadata.json"),
        ],
    )

    assert len(request.files) == 4


def test_upload_complete_request_rejects_unknown_file_name() -> None:
    with pytest.raises(ValidationError, match="unsupported file name"):
        UploadCompleteRequest(
            route_id="route-123",
            upload_session_id="sess_abc123",
            files=[_file("unknown.txt")],
        )


def test_upload_complete_request_rejects_duplicate_file_names() -> None:
    with pytest.raises(ValidationError, match="duplicate file names"):
        UploadCompleteRequest(
            route_id="route-123",
            upload_session_id="sess_abc123",
            files=[_file("gps.json"), _file("gps.json")],
        )


def test_complete_response_serializes_validation_results() -> None:
    response = CompleteResponse(
        route_id="route-123",
        upload_session_id="sess_abc123",
        correlation_id="corr_xyz789",
        validation_status=ValidationStatus.VALIDATED,
        files=[
            FileValidationResult(
                name="gps.json",
                status=FileValidationStatus.VALID,
            ),
        ],
    )

    payload = response.model_dump(mode="json")
    assert payload["validation_status"] == "VALIDATED"
    assert payload["files"][0]["status"] == "VALID"
