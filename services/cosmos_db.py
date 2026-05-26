"""Cosmos DB — trip_ingestion_log CRUD."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from config import Settings, get_settings
from models.enums import TripLogStatus
from models.trip_log import TripLog

COSMOS_EMULATOR_KEY = (
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
)

_HTTP_PRECONDITION_FAILED = 412


def _is_emulator_endpoint(endpoint: str) -> bool:
    """Return True when the endpoint targets the local Cosmos DB emulator."""
    return "localhost" in endpoint or "127.0.0.1" in endpoint


class CosmosDbError(Exception):
    """Base Cosmos DB error."""


class CosmosConfigurationError(CosmosDbError):
    """Cosmos DB service is misconfigured."""


class TripLogNotFoundError(CosmosDbError):
    """Trip log document was not found."""


class CosmosConflictError(CosmosDbError):
    """Optimistic concurrency conflict — document was modified concurrently."""


class CosmosService:
    """Cosmos DB operations for trip ingestion metadata."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        container: Any | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._container = container or self._create_container_client()

    def _create_container_client(self) -> Any:
        endpoint = self._settings.cosmos_endpoint
        if not endpoint:
            raise CosmosConfigurationError("COSMOS_ENDPOINT is not configured")

        if _is_emulator_endpoint(endpoint):
            # Disable endpoint discovery so the SDK stays on localhost:8081
            # instead of following the emulator's internal Docker IP (172.19.x.x).
            os.environ["AZURE_COSMOS_DISABLE_SSL_VERIFICATION"] = "true"
            client = CosmosClient(
                endpoint,
                credential=COSMOS_EMULATOR_KEY,
                connection_verify=False,
                enable_endpoint_discovery=False,
            )
            database = client.create_database_if_not_exists(
                self._settings.cosmos_database,
            )
            return database.create_container_if_not_exists(
                id=self._settings.cosmos_container,
                partition_key=PartitionKey(path="/route_id"),
            )

        client = CosmosClient(endpoint, credential=DefaultAzureCredential())
        database = client.get_database_client(self._settings.cosmos_database)
        return database.get_container_client(self._settings.cosmos_container)

    def create_trip_log(self, trip_log: TripLog) -> TripLog:
        """Create a trip log document in trip_ingestion_log."""
        if trip_log.id != trip_log.upload_session_id:
            raise ValueError("trip log id must match upload_session_id")

        document = trip_log.model_dump(mode="json")
        created = self._container.create_item(body=document)
        return TripLog.model_validate(created)

    def get_trip_log(
        self,
        route_id: str,
        upload_session_id: str,
    ) -> tuple[TripLog | None, str | None]:
        """Load a trip log by partition key and session id.

        Returns:
            A ``(TripLog, etag)`` tuple, or ``(None, None)`` when not found.
            The etag should be passed to :meth:`update_trip_log` to enable
            optimistic concurrency control.
        """
        try:
            item = self._container.read_item(
                item=upload_session_id,
                partition_key=route_id,
            )
        except CosmosResourceNotFoundError:
            return None, None

        etag: str | None = item.get("_etag") if isinstance(item, dict) else None
        return TripLog.model_validate(item), etag

    def trip_exists(self, route_id: str, upload_session_id: str) -> bool:
        """Return True when a trip log exists for the given session."""
        trip_log, _ = self.get_trip_log(route_id, upload_session_id)
        return trip_log is not None

    def update_trip_log(
        self,
        route_id: str,
        upload_session_id: str,
        *,
        etag: str | None = None,
        **fields: Any,
    ) -> tuple[TripLog, str | None]:
        """Update fields on an existing trip log document with optimistic concurrency.

        Args:
            route_id: Cosmos partition key.
            upload_session_id: Document id.
            etag: The ``_etag`` value obtained from the last read. When provided,
                Cosmos will reject the write with a 412 if the document was modified
                concurrently, raising :class:`CosmosConflictError`.
            **fields: Arbitrary fields to merge into the existing document.

        Returns:
            A ``(TripLog, new_etag)`` tuple reflecting the persisted state.

        Raises:
            TripLogNotFoundError: Document does not exist.
            CosmosConflictError: Concurrent modification detected (412).
        """
        existing, read_etag = self.get_trip_log(route_id, upload_session_id)
        if existing is None:
            raise TripLogNotFoundError(
                f"Trip log not found for route_id={route_id} "
                f"upload_session_id={upload_session_id}",
            )

        # Prefer the caller's etag (from original read) for true optimistic locking.
        # Fall back to the etag obtained from the internal re-read.
        effective_etag = etag if etag is not None else read_etag

        update_payload = dict(fields)
        update_payload.setdefault("updated_at", datetime.now(UTC))
        updated = existing.model_copy(update=update_payload)
        document = updated.model_dump(mode="json")

        replace_kwargs: dict[str, Any] = {"item": upload_session_id, "body": document}
        if effective_etag is not None:
            replace_kwargs["if_match"] = effective_etag

        try:
            replaced = self._container.replace_item(**replace_kwargs)
        except CosmosHttpResponseError as exc:
            if exc.status_code == _HTTP_PRECONDITION_FAILED:
                raise CosmosConflictError(
                    f"Concurrent modification on upload_session_id={upload_session_id}",
                ) from exc
            raise CosmosDbError(f"Cosmos replace failed: {exc}") from exc

        new_etag: str | None = replaced.get("_etag") if isinstance(replaced, dict) else None
        return TripLog.model_validate(replaced), new_etag

    @staticmethod
    def new_trip_log(
        *,
        route_id: str,
        upload_session_id: str,
        user_id: str,
        correlation_id: str,
        status: TripLogStatus = TripLogStatus.RECEIVED,
        trip_storage_root: str | None = None,
        trip_file_prefix: str | None = None,
    ) -> TripLog:
        """Build a new trip log ready for persistence."""
        now = datetime.now(UTC)
        return TripLog(
            id=upload_session_id,
            route_id=route_id,
            correlation_id=correlation_id,
            upload_session_id=upload_session_id,
            user_id=user_id,
            status=status,
            created_at=now,
            trip_storage_root=trip_storage_root,
            trip_file_prefix=trip_file_prefix,
        )
