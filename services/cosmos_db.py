"""Cosmos DB — trip_ingestion_log CRUD."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from config import Settings, get_settings
from models.enums import TripLogStatus
from models.trip_log import TripLog

COSMOS_EMULATOR_KEY = (
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
)


class CosmosDbError(Exception):
    """Base Cosmos DB error."""


class CosmosConfigurationError(CosmosDbError):
    """Cosmos DB service is misconfigured."""


class TripLogNotFoundError(CosmosDbError):
    """Trip log document was not found."""


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

        if "localhost" in endpoint:
            client = CosmosClient(endpoint, credential=COSMOS_EMULATOR_KEY)
        else:
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

    def get_trip_log(self, route_id: str, upload_session_id: str) -> TripLog | None:
        """Load a trip log by partition key and session id."""
        try:
            item = self._container.read_item(
                item=upload_session_id,
                partition_key=route_id,
            )
        except CosmosResourceNotFoundError:
            return None

        return TripLog.model_validate(item)

    def trip_exists(self, route_id: str, upload_session_id: str) -> bool:
        """Return True when a trip log exists for the given session."""
        return self.get_trip_log(route_id, upload_session_id) is not None

    def update_trip_log(
        self,
        route_id: str,
        upload_session_id: str,
        **fields: Any,
    ) -> TripLog:
        """Update fields on an existing trip log document."""
        existing = self.get_trip_log(route_id, upload_session_id)
        if existing is None:
            raise TripLogNotFoundError(
                f"Trip log not found for route_id={route_id} "
                f"upload_session_id={upload_session_id}",
            )

        update_payload = dict(fields)
        update_payload.setdefault("updated_at", datetime.now(UTC))
        updated = existing.model_copy(update=update_payload)
        document = updated.model_dump(mode="json")
        replaced = self._container.replace_item(
            item=upload_session_id,
            body=document,
        )
        return TripLog.model_validate(replaced)

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
