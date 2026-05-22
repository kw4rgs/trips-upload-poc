"""Integration tests for BlobStorageService against Azurite."""

from __future__ import annotations

import os
import socket
from datetime import UTC, datetime

import pytest

from config import Settings
from models.enums import TripSource
from services.blob_storage import BlobStorageService

AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUz1HT2LtL7vADFjPUPE=;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)


def _azurite_is_reachable(host: str = "127.0.0.1", port: int = 10000) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def azurite_connection_string() -> str | None:
    """Return Azurite connection string when emulator is reachable."""
    if not _azurite_is_reachable():
        return None

    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", AZURITE_CONNECTION_STRING)
    try:
        service = BlobStorageService(
            settings=Settings(
                storage_container="landing",
                use_azurite=True,
                azure_webjobs_storage=connection_string,
            ),
        )
        service.ensure_container()
    except Exception:
        return None
    return connection_string


@pytest.fixture
def blob_service(azurite_connection_string: str | None) -> BlobStorageService:
    if azurite_connection_string is None:
        pytest.skip("Azurite is not available on localhost:10000")
    return BlobStorageService(
        settings=Settings(
            storage_container="landing",
            use_azurite=True,
            azure_webjobs_storage=azurite_connection_string,
            sas_ttl_minutes=15,
        ),
    )


@pytest.mark.integration
def test_upload_exists_and_properties(blob_service: BlobStorageService) -> None:
    timestamp = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)
    blob_path = blob_service.build_upload_target_path(
        TripSource.GPS,
        "user-123",
        "route-456",
        timestamp,
    )
    payload = b'{"lat": 1.0, "lon": 2.0}'

    blob_service.upload_blob(blob_path, payload)

    assert blob_service.blob_exists(blob_path) is True
    properties = blob_service.get_blob_properties(blob_path)
    assert properties.size == len(payload)
    assert blob_service.download_blob(blob_path) == payload


@pytest.mark.integration
def test_generate_sas_allows_client_upload(blob_service: BlobStorageService) -> None:
    import urllib.request

    timestamp = datetime(2026, 5, 22, 13, 0, tzinfo=UTC)
    blob_path = blob_service.build_upload_target_path(
        TripSource.METADATA,
        "user-789",
        "route-999",
        timestamp,
    )
    payload = b'{"trip": "metadata"}'
    sas = blob_service.generate_sas(blob_path)

    request = urllib.request.Request(
        sas.sas_url,
        data=payload,
        method="PUT",
        headers={
            "x-ms-blob-type": "BlockBlob",
            "Content-Length": str(len(payload)),
        },
    )
    with urllib.request.urlopen(request) as response:
        assert response.status in {200, 201}

    assert blob_service.blob_exists(blob_path) is True
