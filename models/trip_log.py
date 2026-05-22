"""Pydantic schema for trip_ingestion_log Cosmos documents."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.enums import TripLogStatus


class TripLog(BaseModel):
    """Operational metadata for a trip upload session."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, description="Cosmos document id")
    route_id: str = Field(min_length=1, description="Cosmos partition key")
    correlation_id: str = Field(min_length=1)
    upload_session_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    status: TripLogStatus
    validation_status: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    gps_exists: bool = False
    imu_exists: bool = False
    bt_exists: bool = False
    metadata_exists: bool = False
    trip_storage_root: str | None = None
    trip_file_prefix: str | None = None
