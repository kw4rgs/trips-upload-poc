"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Upload Service."""

    model_config = SettingsConfigDict(extra="ignore")

    storage_account_name: str = ""
    storage_container: str = "landing"
    cosmos_endpoint: str = ""
    cosmos_database: str = "trips"
    cosmos_container: str = "trip_ingestion_log"
    eventhub_name: str = "trip-processing-eventhub"
    eventhub_fully_qualified_namespace: str = ""
    jwt_mock_secret: str = ""
    jwt_mock_user_id: str = ""
    sas_ttl_minutes: int = 15
    applicationinsights_connection_string: str = ""


def get_settings() -> Settings:
    """Return settings instance (env vars / app settings)."""
    return Settings()
