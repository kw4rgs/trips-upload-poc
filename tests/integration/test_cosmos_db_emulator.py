"""Integration tests for CosmosService against the Cosmos DB emulator."""

from __future__ import annotations

import os
import socket
import uuid

import pytest

from config import Settings
from models.enums import TripLogStatus
from services.cosmos_db import CosmosService

COSMOS_EMULATOR_ENDPOINT = os.getenv(
    "COSMOS_ENDPOINT",
    "https://localhost:8081/",
)


def _cosmos_emulator_is_reachable(host: str = "127.0.0.1", port: int = 8081) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def cosmos_service() -> CosmosService | None:
    if not _cosmos_emulator_is_reachable():
        return None

    try:
        service = CosmosService(
            settings=Settings(
                cosmos_endpoint=COSMOS_EMULATOR_ENDPOINT,
                cosmos_database="trips",
                cosmos_container="trip_ingestion_log",
            ),
        )
        return service
    except Exception:
        return None


@pytest.fixture
def cosmos_crud_service(cosmos_service: CosmosService | None) -> CosmosService:
    if cosmos_service is None:
        pytest.skip("Cosmos DB emulator is not available on localhost:8081")
    return cosmos_service


@pytest.mark.integration
def test_trip_log_crud_lifecycle(cosmos_crud_service: CosmosService) -> None:
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    route_id = f"route-{uuid.uuid4().hex[:8]}"

    trip_log = cosmos_crud_service.new_trip_log(
        route_id=route_id,
        upload_session_id=session_id,
        user_id="user-integration",
        correlation_id=f"corr_{uuid.uuid4().hex[:8]}",
    )

    created = cosmos_crud_service.create_trip_log(trip_log)
    assert created.status == TripLogStatus.RECEIVED
    assert cosmos_crud_service.trip_exists(route_id, session_id) is True

    updated = cosmos_crud_service.update_trip_log(
        route_id,
        session_id,
        status=TripLogStatus.VALIDATED,
        validation_status="VALIDATED",
        gps_exists=True,
    )
    assert updated.status == TripLogStatus.VALIDATED
    assert updated.gps_exists is True

    loaded = cosmos_crud_service.get_trip_log(route_id, session_id)
    assert loaded is not None
    assert loaded.validation_status == "VALIDATED"
