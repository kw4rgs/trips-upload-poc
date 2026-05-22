"""Upload complete orchestration."""

from __future__ import annotations

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


class TripOwnershipError(Exception):
    """Caller does not own the requested trip session."""


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
        caller_user_id: str,
    ) -> CompleteResponse:
        """Validate uploaded files and publish metadata when all files pass.

        Ownership is enforced: ``caller_user_id`` must match the ``user_id``
        recorded on the trip log at session creation time.

        A deterministic ``event_id`` (derived from ``upload_session_id``) is
        stored on the trip log *before* publishing to Event Hub.  This allows
        downstream consumers to deduplicate re-delivered events and makes the
        publish step idempotent on retry.

        Optimistic concurrency (etag) is threaded through every Cosmos write to
        detect concurrent complete requests early and return 409.
        """
        trip_log, etag = self._cosmos.get_trip_log(request.route_id, request.upload_session_id)
        if trip_log is None:
            raise TripLogNotFoundError(
                f"Trip log not found for route_id={request.route_id} "
                f"upload_session_id={request.upload_session_id}",
            )

        if trip_log.user_id != caller_user_id:
            raise TripOwnershipError(
                f"upload_session_id={request.upload_session_id} belongs to a different user",
            )

        if trip_log.status == TripLogStatus.PUBLISHED:
            return self._build_idempotent_response(trip_log, correlation_id)

        # Deterministic event_id: same value on every retry so Event Hub
        # consumers can deduplicate by event_id without extra state.
        det_event_id = f"evt_{request.upload_session_id}"

        # Mark VALIDATING using the original etag — any concurrent request
        # will hit a 412 on this write and receive a 409 from the endpoint.
        _, etag = self._cosmos.update_trip_log(
            request.route_id,
            request.upload_session_id,
            etag=etag,
            status=TripLogStatus.VALIDATING,
        )

        file_results = [
            self._validate_file(trip_log, file_descriptor)
            for file_descriptor in request.files
        ]
        all_valid = all(result.status == FileValidationStatus.VALID for result in file_results)
        validation_status = ValidationStatus.VALIDATED if all_valid else ValidationStatus.FAILED

        source_flags = self._source_flags(file_results)

        # Store event_id on the trip log *before* publishing so that, if the
        # publish succeeds but the PUBLISHED update fails, a retry can detect
        # the deterministic event_id and skip a duplicate publish.
        _, etag = self._cosmos.update_trip_log(
            request.route_id,
            request.upload_session_id,
            etag=etag,
            status=TripLogStatus.VALIDATED if all_valid else TripLogStatus.FAILED,
            validation_status=validation_status.value,
            event_id=det_event_id if all_valid else None,
            **source_flags,
        )

        if all_valid:
            self._publish_event(trip_log, request, correlation_id, source_flags, det_event_id)
            self._cosmos.update_trip_log(
                request.route_id,
                request.upload_session_id,
                etag=etag,
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
        event_id: str,
    ) -> None:
        available_sources = [
            TripSource(source_name.removesuffix("_exists"))
            for source_name, exists in source_flags.items()
            if exists
        ]
        event = TripEvent(
            event_id=event_id,
            correlation_id=correlation_id,
            trip_id=trip_log.upload_session_id,
            route_id=request.route_id,
            user_id=trip_log.user_id,
            upload_session_id=request.upload_session_id,
            trip_date=trip_log.created_at.date(),
            uploaded_at=datetime.now(UTC),
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
