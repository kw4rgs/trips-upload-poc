"""Pydantic schemas for upload complete request/response."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

EXPECTED_FILE_NAMES: frozenset[str] = frozenset(
    {"gps.json", "imu.bin", "bt.json", "metadata.json"},
)


class ValidationStatus(StrEnum):
    """Aggregate validation outcome for an upload complete request."""

    VALIDATED = "VALIDATED"
    FAILED = "FAILED"


class FileValidationStatus(StrEnum):
    """Per-file validation outcome."""

    VALID = "VALID"
    FAILED = "FAILED"


class FileDescriptor(BaseModel):
    """Client-reported blob metadata for validation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    size: int = Field(ge=0)
    checksum: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_known_file_name(cls, value: str) -> str:
        if value not in EXPECTED_FILE_NAMES:
            expected = ", ".join(sorted(EXPECTED_FILE_NAMES))
            raise ValueError(f"unsupported file name '{value}'; expected one of: {expected}")
        return value


class UploadCompleteRequest(BaseModel):
    """POST /api/upload/complete body."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    route_id: str = Field(min_length=1)
    upload_session_id: str = Field(min_length=1)
    files: list[FileDescriptor] = Field(min_length=1)

    @field_validator("files")
    @classmethod
    def validate_unique_file_names(
        cls,
        files: list[FileDescriptor],
    ) -> list[FileDescriptor]:
        names = [file.name for file in files]
        if len(names) != len(set(names)):
            raise ValueError("duplicate file names are not allowed")
        return files


class FileValidationResult(BaseModel):
    """Validation result for a single uploaded file."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    status: FileValidationStatus
    error: str | None = None


class CompleteResponse(BaseModel):
    """POST /api/upload/complete success response."""

    model_config = ConfigDict(extra="forbid")

    route_id: str = Field(min_length=1)
    upload_session_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    validation_status: ValidationStatus
    files: list[FileValidationResult] = Field(min_length=1)
