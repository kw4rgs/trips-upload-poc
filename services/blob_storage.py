"""Blob Storage — User Delegation SAS, exists, properties."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    generate_blob_sas,
)

from config import Settings, get_settings
from models.enums import TripSource

SOURCE_FILE_NAMES: dict[TripSource, str] = {
    TripSource.GPS: "gps.json",
    TripSource.IMU: "imu.bin",
    TripSource.BT: "bt.json",
    TripSource.METADATA: "metadata.json",
}


class BlobStorageError(Exception):
    """Base blob storage error."""


class BlobStorageConfigurationError(BlobStorageError):
    """Blob storage service is misconfigured."""


class BlobNotFoundError(BlobStorageError):
    """Requested blob does not exist."""


@dataclass(frozen=True)
class BlobObjectProperties:
    """Subset of blob properties used by upload validation."""

    name: str
    size: int
    etag: str | None = None
    content_md5: bytes | None = None


@dataclass(frozen=True)
class GeneratedSas:
    """SAS generation result for a blob upload target."""

    blob_path: str
    sas_url: str
    expires_at: datetime


def build_trip_file_name(
    source: TripSource,
    user_id: str,
    route_id: str,
    timestamp: datetime,
) -> str:
    """Build the canonical blob file name for a trip source."""
    ts = timestamp.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}_{user_id}_{route_id}_{SOURCE_FILE_NAMES[source]}"


def build_blob_path(source: TripSource, timestamp: datetime, file_name: str) -> str:
    """Build the blob path inside the landing container."""
    ts = timestamp.astimezone(UTC)
    return (
        f"source={source.value}/"
        f"year={ts.year:04d}/month={ts.month:02d}/day={ts.day:02d}/"
        f"{file_name}"
    )


def build_trip_storage_root(timestamp: datetime) -> str:
    """Build the trip storage root prefix used in trip events."""
    ts = timestamp.astimezone(UTC)
    return f"year={ts.year:04d}/month={ts.month:02d}/day={ts.day:02d}/"


class BlobStorageService:
    """Azure Blob Storage operations for trip uploads."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: BlobServiceClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or self._create_client()
        self._container_client = self._client.get_container_client(
            self._settings.storage_container,
        )

    def _create_client(self) -> BlobServiceClient:
        if self._settings.azure_webjobs_storage:
            return BlobServiceClient.from_connection_string(
                self._settings.azure_webjobs_storage,
            )

        if not self._settings.storage_account_name:
            raise BlobStorageConfigurationError("STORAGE_ACCOUNT_NAME is not configured")

        account_url = (
            f"https://{self._settings.storage_account_name}.blob.core.windows.net"
        )
        return BlobServiceClient(account_url, credential=DefaultAzureCredential())

    @property
    def uses_connection_string(self) -> bool:
        """Return True when running against a connection string (e.g. Azurite)."""
        return bool(self._settings.azure_webjobs_storage)

    def ensure_container(self) -> None:
        """Create the landing container when it does not exist."""
        if not self._container_client.exists():
            self._container_client.create_container()

    def build_upload_target_path(
        self,
        source: TripSource,
        user_id: str,
        route_id: str,
        timestamp: datetime,
    ) -> str:
        """Build the full blob path for a trip source upload target."""
        file_name = build_trip_file_name(source, user_id, route_id, timestamp)
        return build_blob_path(source, timestamp, file_name)

    def generate_sas(
        self,
        blob_path: str,
        ttl_minutes: int | None = None,
    ) -> GeneratedSas:
        """Generate a write-only SAS URL for direct client upload."""
        ttl = ttl_minutes if ttl_minutes is not None else self._settings.sas_ttl_minutes
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=ttl)

        if self.uses_connection_string:
            sas_token = self._generate_account_key_sas(blob_path, expires_at)
        else:
            sas_token = self._generate_user_delegation_sas(blob_path, now, expires_at)

        blob_client = self._container_client.get_blob_client(blob_path)
        return GeneratedSas(
            blob_path=blob_path,
            sas_url=f"{blob_client.url}?{sas_token}",
            expires_at=expires_at,
        )

    def _generate_account_key_sas(
        self,
        blob_path: str,
        expires_at: datetime,
    ) -> str:
        credential = self._client.credential
        account_key = getattr(credential, "account_key", None)
        if account_key is None:
            raise BlobStorageConfigurationError(
                "Connection string credential does not expose an account key",
            )

        return generate_blob_sas(
            account_name=self._client.account_name,
            container_name=self._settings.storage_container,
            blob_name=blob_path,
            account_key=account_key,
            permission=BlobSasPermissions(write=True, create=True),
            expiry=expires_at,
        )

    def _generate_user_delegation_sas(
        self,
        blob_path: str,
        start_time: datetime,
        expires_at: datetime,
    ) -> str:
        if not self._settings.storage_account_name:
            raise BlobStorageConfigurationError("STORAGE_ACCOUNT_NAME is not configured")

        delegation_key = self._client.get_user_delegation_key(
            key_start_time=start_time,
            key_expiry_time=expires_at,
        )
        return generate_blob_sas(
            account_name=self._settings.storage_account_name,
            container_name=self._settings.storage_container,
            blob_name=blob_path,
            user_delegation_key=delegation_key,
            permission=BlobSasPermissions(write=True, create=True),
            expiry=expires_at,
        )

    def blob_exists(self, blob_path: str) -> bool:
        """Return True when the blob exists in the landing container."""
        return self._container_client.get_blob_client(blob_path).exists()

    def get_blob_properties(self, blob_path: str) -> BlobObjectProperties:
        """Return blob properties used for upload validation."""
        blob_client = self._container_client.get_blob_client(blob_path)
        try:
            properties = blob_client.get_blob_properties()
        except ResourceNotFoundError as exc:
            raise BlobNotFoundError(f"Blob not found: {blob_path}") from exc

        content_md5 = None
        if properties.content_settings is not None:
            content_md5 = properties.content_settings.content_md5

        return BlobObjectProperties(
            name=blob_path,
            size=properties.size,
            etag=properties.etag,
            content_md5=content_md5,
        )

    def download_blob(self, blob_path: str) -> bytes:
        """Download blob contents."""
        blob_client = self._container_client.get_blob_client(blob_path)
        try:
            return blob_client.download_blob().readall()
        except ResourceNotFoundError as exc:
            raise BlobNotFoundError(f"Blob not found: {blob_path}") from exc

    def upload_blob(self, blob_path: str, data: bytes) -> None:
        """Upload blob contents (testing and admin helpers)."""
        blob_client = self._container_client.get_blob_client(blob_path)
        blob_client.upload_blob(data, overwrite=True)
