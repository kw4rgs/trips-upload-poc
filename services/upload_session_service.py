"""Upload session orchestration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from config import Settings, get_settings
from models.enums import TripSource
from models.session import UploadSessionResponse, UploadTarget
from services.blob_storage import BlobStorageService, build_trip_file_prefix, build_trip_storage_root
from services.cosmos_db import CosmosService


class UploadSessionService:
    """Create upload sessions with SAS URLs and trip log metadata."""

    def __init__(
        self,
        *,
        blob_service: BlobStorageService | None = None,
        cosmos_service: CosmosService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._blob = blob_service or BlobStorageService(self._settings)
        self._cosmos = cosmos_service or CosmosService(self._settings)

    def create_session(
        self,
        *,
        route_id: str,
        user_id: str,
        correlation_id: str,
    ) -> UploadSessionResponse:
        """Create SAS targets and persist the initial trip log."""
        upload_session_id = f"sess_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(UTC)
        trip_storage_root = build_trip_storage_root(timestamp)
        trip_file_prefix = build_trip_file_prefix(user_id, route_id, timestamp)

        uploads: dict[TripSource, UploadTarget] = {}
        expires_at: datetime | None = None

        for source in TripSource:
            blob_path = self._blob.build_upload_target_path(
                source,
                user_id,
                route_id,
                timestamp,
            )
            sas = self._blob.generate_sas(blob_path)
            expires_at = sas.expires_at
            uploads[source] = UploadTarget(
                source=source,
                blob_path=blob_path,
                sas_url=sas.sas_url,
            )

        if expires_at is None:
            raise RuntimeError("no upload targets were generated")

        trip_log = self._cosmos.new_trip_log(
            route_id=route_id,
            upload_session_id=upload_session_id,
            user_id=user_id,
            correlation_id=correlation_id,
            trip_storage_root=trip_storage_root,
            trip_file_prefix=trip_file_prefix,
        )
        self._cosmos.create_trip_log(trip_log)

        return UploadSessionResponse(
            upload_session_id=upload_session_id,
            route_id=route_id,
            user_id=user_id,
            correlation_id=correlation_id,
            expires_at=expires_at,
            uploads=uploads,
        )
