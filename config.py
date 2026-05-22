"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Upload Service.

    Environment routing
    -------------------
    ``ENVIRONMENT=local``  → Azurite (blob) + Cosmos emulator + Kafka/Redpanda
    ``ENVIRONMENT=production`` (default) → Azure Blob + Azure Cosmos + Azure Event Hub

    Set ``USE_AZURITE=true`` to route blob operations through a connection
    string (``AzureWebJobsStorage``) instead of Managed Identity.  This flag
    is intentionally separate from ``AzureWebJobsStorage`` so the Functions
    runtime storage does not silently bypass MI in production.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- Environment routing ---
    environment: str = Field(
        default="production",
        description="Runtime environment: 'local' or 'production'",
    )

    # --- Blob Storage ---
    storage_account_name: str = Field(default="", description="Blob storage account name")
    storage_container: str = Field(default="landing", description="Blob container for trip files")
    use_azurite: bool = Field(
        default=False,
        description="Route blob operations through Azurite connection string",
    )
    azure_webjobs_storage: str = Field(
        default="",
        validation_alias="AzureWebJobsStorage",
        description="Functions runtime storage connection string (runtime only — do not use for data plane in prod)",
    )

    # --- Cosmos DB ---
    cosmos_endpoint: str = Field(default="", description="Cosmos DB account URI")
    cosmos_database: str = Field(default="trips", description="Cosmos database name")
    cosmos_container: str = Field(
        default="trip_ingestion_log",
        description="Cosmos container for trip metadata",
    )

    # --- Event Hub (production) ---
    eventhub_name: str = Field(
        default="trip-processing-eventhub",
        description="Event Hub name for trip events",
    )
    eventhub_fully_qualified_namespace: str = Field(
        default="",
        description="Event Hub namespace FQDN (production only)",
    )

    # --- Kafka (local dev) ---
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka broker address for local development (Redpanda in Docker)",
    )
    kafka_topic: str = Field(
        default="trip-processing",
        description="Kafka topic name used by KafkaPublisher in local environment",
    )

    # --- Auth ---
    jwt_mock_secret: str = Field(default="", description="POC JWT signing secret")
    jwt_mock_user_id: str = Field(default="", description="POC default user id (test only)")
    sas_ttl_minutes: int = Field(default=15, description="SAS token TTL in minutes")

    # --- Observability ---
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

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        allowed = {"local", "production"}
        if value not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got '{value}'")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance (env vars / app settings)."""
    return Settings()
