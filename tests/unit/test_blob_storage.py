"""Unit tests for blob path helpers and BlobStorageService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError

from models.enums import TripSource
from services.blob_storage import (
    BlobNotFoundError,
    BlobStorageService,
    build_blob_path,
    build_trip_file_name,
    build_trip_storage_root,
)


def test_build_trip_file_name_uses_canonical_pattern() -> None:
    timestamp = datetime(2026, 5, 22, 12, 13, 14, tzinfo=UTC)
    file_name = build_trip_file_name(TripSource.GPS, "123", "aaa-4567", timestamp)
    assert file_name == "20260522T121314Z_123_aaa-4567_gps.json"


def test_build_blob_path_includes_source_and_date_partitions() -> None:
    timestamp = datetime(2026, 5, 22, 12, 13, 14, tzinfo=UTC)
    blob_path = build_blob_path(
        TripSource.IMU,
        timestamp,
        "20260522T121314Z_123_aaa-4567_imu.bin",
    )
    assert blob_path == "source=imu/year=2026/month=05/day=22/20260522T121314Z_123_aaa-4567_imu.bin"


def test_build_trip_storage_root() -> None:
    timestamp = datetime(2026, 5, 5, 12, 13, 14, tzinfo=UTC)
    assert build_trip_storage_root(timestamp) == "year=2026/month=05/day=05/"


def test_blob_exists_returns_true(settings) -> None:
    settings.azure_webjobs_storage = (
        "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUz1HT2LtL7vADFjPUPE=;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    )
    mock_blob_client = MagicMock()
    mock_blob_client.exists.return_value = True

    mock_container_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service_client = MagicMock()
    mock_service_client.get_container_client.return_value = mock_container_client

    with patch(
        "services.blob_storage.BlobServiceClient.from_connection_string",
        return_value=mock_service_client,
    ):
        service = BlobStorageService(settings=settings)
        assert service.blob_exists("source=gps/year=2026/month=05/day=22/file.json") is True


def test_get_blob_properties_raises_when_missing(settings) -> None:
    settings.azure_webjobs_storage = (
        "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUz1HT2LtL7vADFjPUPE=;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    )
    mock_blob_client = MagicMock()
    mock_blob_client.get_blob_properties.side_effect = ResourceNotFoundError("missing")

    mock_container_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service_client = MagicMock()
    mock_service_client.get_container_client.return_value = mock_container_client

    with patch(
        "services.blob_storage.BlobServiceClient.from_connection_string",
        return_value=mock_service_client,
    ):
        service = BlobStorageService(settings=settings)
        with pytest.raises(BlobNotFoundError):
            service.get_blob_properties("missing/blob.json")


def test_generate_sas_uses_account_key_for_connection_string_mode(settings) -> None:
    settings.azure_webjobs_storage = (
        "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUz1HT2LtL7vADFjPUPE=;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    )
    mock_blob_client = MagicMock()
    type(mock_blob_client).url = PropertyMock(
        return_value="http://127.0.0.1:10000/devstoreaccount1/landing/blob.json",
    )

    mock_container_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_service_client = MagicMock()
    mock_service_client.account_name = "devstoreaccount1"
    mock_credential = MagicMock()
    mock_credential.account_key = "test-account-key"
    mock_service_client.credential = mock_credential
    mock_service_client.get_container_client.return_value = mock_container_client

    with patch(
        "services.blob_storage.BlobServiceClient.from_connection_string",
        return_value=mock_service_client,
    ), patch(
        "services.blob_storage.generate_blob_sas",
        return_value="sig=mock",
    ) as generate_sas_mock:
        service = BlobStorageService(settings=settings)
        result = service.generate_sas("source=gps/year=2026/month=05/day=22/file.json")

    assert result.sas_url.endswith("?sig=mock")
    assert result.blob_path.endswith("file.json")
    generate_sas_mock.assert_called_once()
