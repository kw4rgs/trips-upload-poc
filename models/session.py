"""Pydantic schemas for upload session request/response."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.enums import TRIP_UPLOAD_SOURCES, TripSource


class UploadSessionRequest(BaseModel):
    """POST /api/upload/session body."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    route_id: str = Field(min_length=1, description="Unique route identifier from mobile app")


class UploadTarget(BaseModel):
    """SAS target for a single trip data source."""

    model_config = ConfigDict(extra="forbid")

    source: TripSource
    blob_path: str = Field(min_length=1)
    sas_url: str = Field(min_length=1)


class UploadSessionResponse(BaseModel):
    """POST /api/upload/session success response."""

    model_config = ConfigDict(extra="forbid")

    upload_session_id: str = Field(min_length=1)
    route_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    expires_at: datetime
    uploads: dict[TripSource, UploadTarget]

    @field_validator("uploads")
    @classmethod
    def validate_all_sources_present(
        cls,
        uploads: dict[TripSource, UploadTarget],
    ) -> dict[TripSource, UploadTarget]:
        missing = TRIP_UPLOAD_SOURCES - set(uploads)
        if missing:
            missing_names = ", ".join(sorted(source.value for source in missing))
            raise ValueError(f"missing upload targets for sources: {missing_names}")
        return uploads
