"""Pydantic schema for Event Hub trip events."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.enums import TripSource


class TripEvent(BaseModel):
    """Metadata-only event published after successful upload validation."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    trip_id: str = Field(min_length=1)
    route_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    upload_session_id: str = Field(min_length=1)
    trip_date: date
    uploaded_at: datetime
    available_sources: list[TripSource] = Field(min_length=1)
    trip_storage_root: str = Field(min_length=1)
    trip_file_prefix: str = Field(min_length=1)

    @field_validator("available_sources")
    @classmethod
    def validate_unique_sources(cls, sources: list[TripSource]) -> list[TripSource]:
        if len(sources) != len(set(sources)):
            raise ValueError("available_sources must not contain duplicates")
        return sources
