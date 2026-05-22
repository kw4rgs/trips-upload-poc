"""Shared enumerations for trip upload domain models."""

from enum import StrEnum


class TripSource(StrEnum):
    """Supported blob sources for a trip upload session."""

    GPS = "gps"
    IMU = "imu"
    BT = "bt"
    METADATA = "metadata"


TRIP_UPLOAD_SOURCES: frozenset[TripSource] = frozenset(TripSource)


class TripLogStatus(StrEnum):
    """Lifecycle status persisted in trip_ingestion_log."""

    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    PUBLISHED = "PUBLISHED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    PARTIALLY_PROCESSED = "PARTIALLY_PROCESSED"
    FAILED = "FAILED"
