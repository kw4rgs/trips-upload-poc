"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Upload Service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    storage_account_name: str = Field(default="", description="Blob storage account name")
    storage_container: str = Field(default="landing", description="Blob container for trip files")
    cosmos_endpoint: str = Field(default="", description="Cosmos DB account URI")
    cosmos_database: str = Field(default="trips", description="Cosmos database name")
    cosmos_container: str = Field(
        default="trip_ingestion_log",
        description="Cosmos container for trip metadata",
    )
    eventhub_name: str = Field(
        default="trip-processing-eventhub",
        description="Event Hub name for trip events",
    )
    eventhub_fully_qualified_namespace: str = Field(
        default="",
        description="Event Hub namespace FQDN",
    )
    jwt_mock_secret: str = Field(default="", description="POC JWT signing secret")
    jwt_mock_user_id: str = Field(default="", description="POC default user id")
    sas_ttl_minutes: int = Field(default=15, description="SAS token TTL in minutes")
    applicationinsights_connection_string: str = Field(
        default="",
        description="Application Insights connection string",
    )

    @field_validator("sas_ttl_minutes")
    @classmethod
    def validate_sas_ttl(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("sas_ttl_minutes must be greater than zero")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance (env vars / app settings)."""
    return Settings()
