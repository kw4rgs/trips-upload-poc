"""Upload complete orchestration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from config import Settings, get_settings
from models.complete import (
    CompleteResponse,
    FileDescriptor,
    FileValidationResult,
    FileValidationStatus,
    UploadCompleteRequest,
    ValidationStatus,
)
from models.enums import TripLogStatus, TripSource
from models.trip_event import TripEvent
from models.trip_log import TripLog
from services.blob_storage import (
    BlobNotFoundError,
    BlobStorageService,
    SOURCE_FILE_NAMES,
    build_blob_path,
)
from services.cosmos_db import CosmosService, TripLogNotFoundError
from services.event_hub import EventHubService
from shared.checksum import checksum_matches

FILE_NAME_TO_SOURCE: dict[str, TripSource] = {
    file_name: source for source, file_name in SOURCE_FILE_NAMES.items()
}


class UploadCompleteService:
    """Validate uploaded blobs and publish trip events."""

    def __init__(
        self,
        *,
        blob_service: BlobStorageService | None = None,
        cosmos_service: CosmosService | None = None,
        event_hub_service: EventHubService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._blob = blob_service or BlobStorageService(self._settings)
        self._cosmos = cosmos_service or CosmosService(self._settings)
        self._event_hub = event_hub_service or EventHubService(self._settings)

    def complete_upload(
        self,
        *,
        request: UploadCompleteRequest,
        correlation_id: str,
    ) -> CompleteResponse:
        """Validate uploaded files and publish metadata when successful."""
        trip_log = self._cosmos.get_trip_log(request.route_id, request.upload_session_id)
        if trip_log is None:
            raise TripLogNotFoundError(
                f"Trip log not found for route_id={request.route_id} "
                f"upload_session_id={request.upload_session_id}",
            )

        if trip_log.status == TripLogStatus.PUBLISHED:
            return self._build_idempotent_response(trip_log, correlation_id)

        self._cosmos.update_trip_log(
            request.route_id,
            request.upload_session_id,
            status=TripLogStatus.VALIDATING,
        )

        file_results = [
            self._validate_file(trip_log, file_descriptor)
            for file_descriptor in request.files
        ]
        all_valid = all(result.status == FileValidationStatus.VALID for result in file_results)
        validation_status = ValidationStatus.VALIDATED if all_valid else ValidationStatus.FAILED

        source_flags = self._source_flags(file_results)
        self._cosmos.update_trip_log(
            request.route_id,
            request.upload_session_id,
            status=TripLogStatus.VALIDATED if all_valid else TripLogStatus.FAILED,
            validation_status=validation_status.value,
            **source_flags,
        )

        if all_valid:
            self._publish_event(trip_log, request, correlation_id, source_flags)
            self._cosmos.update_trip_log(
                request.route_id,
                request.upload_session_id,
                status=TripLogStatus.PUBLISHED,
            )

        return CompleteResponse(
            route_id=request.route_id,
            upload_session_id=request.upload_session_id,
            correlation_id=correlation_id,
            validation_status=validation_status,
            files=file_results,
        )

    def _validate_file(
        self,
        trip_log: TripLog,
        file_descriptor: FileDescriptor,
    ) -> FileValidationResult:
        if trip_log.trip_file_prefix is None:
            return FileValidationResult(
                name=file_descriptor.name,
                status=FileValidationStatus.FAILED,
                error="trip_file_prefix missing from trip log",
            )

        source = FILE_NAME_TO_SOURCE[file_descriptor.name]
        blob_file_name = f"{trip_log.trip_file_prefix}_{file_descriptor.name}"
        blob_path = build_blob_path(source, trip_log.created_at, blob_file_name)

        try:
            if not self._blob.blob_exists(blob_path):
                return FileValidationResult(
                    name=file_descriptor.name,
                    status=FileValidationStatus.FAILED,
                    error="blob not found",
                )

            properties = self._blob.get_blob_properties(blob_path)
            if properties.size != file_descriptor.size:
                return FileValidationResult(
                    name=file_descriptor.name,
                    status=FileValidationStatus.FAILED,
                    error="size mismatch",
                )

            if not checksum_matches(
                file_descriptor.checksum,
                content_md5=properties.content_md5,
            ):
                data = self._blob.download_blob(blob_path)
                if not checksum_matches(file_descriptor.checksum, data=data):
                    return FileValidationResult(
                        name=file_descriptor.name,
                        status=FileValidationStatus.FAILED,
                        error="checksum mismatch",
                    )
        except BlobNotFoundError:
            return FileValidationResult(
                name=file_descriptor.name,
                status=FileValidationStatus.FAILED,
                error="blob not found",
            )

        return FileValidationResult(
            name=file_descriptor.name,
            status=FileValidationStatus.VALID,
        )

    def _source_flags(self, file_results: list[FileValidationResult]) -> dict[str, bool]:
        flags = {
            "gps_exists": False,
            "imu_exists": False,
            "bt_exists": False,
            "metadata_exists": False,
        }
        for result in file_results:
            if result.status != FileValidationStatus.VALID:
                continue
            source = FILE_NAME_TO_SOURCE[result.name]
            flags[f"{source.value}_exists"] = True
        return flags

    def _publish_event(
        self,
        trip_log: TripLog,
        request: UploadCompleteRequest,
        correlation_id: str,
        source_flags: dict[str, bool],
    ) -> None:
        available_sources = [
            TripSource(source_name.removesuffix("_exists"))
            for source_name, exists in source_flags.items()
            if exists
        ]
        uploaded_at = datetime.now(UTC)
        event = TripEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            correlation_id=correlation_id,
            trip_id=trip_log.upload_session_id.removeprefix("sess_"),
            route_id=request.route_id,
            user_id=trip_log.user_id,
            upload_session_id=request.upload_session_id,
            trip_date=trip_log.created_at.date(),
            uploaded_at=uploaded_at,
            available_sources=available_sources,
            trip_storage_root=trip_log.trip_storage_root or "",
            trip_file_prefix=trip_log.trip_file_prefix or "",
        )
        self._event_hub.publish_trip_event(event)

    @staticmethod
    def _build_idempotent_response(trip_log: TripLog, correlation_id: str) -> CompleteResponse:
        files = [
            FileValidationResult(name=file_name, status=FileValidationStatus.VALID)
            for file_name in sorted(FILE_NAME_TO_SOURCE)
        ]
        return CompleteResponse(
            route_id=trip_log.route_id,
            upload_session_id=trip_log.upload_session_id,
            correlation_id=correlation_id,
            validation_status=ValidationStatus.VALIDATED,
            files=files,
        )
