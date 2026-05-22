"""Unit tests for application settings."""

import pytest

from config import Settings, get_settings


def test_settings_load_from_environment(settings) -> None:
    assert settings.storage_account_name == "teststorage"
    assert settings.storage_container == "landing"
    assert settings.cosmos_database == "trips"
    assert settings.sas_ttl_minutes == 15


def test_get_settings_is_cached(settings) -> None:
    assert get_settings() is get_settings()


def test_sas_ttl_must_be_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAS_TTL_MINUTES", "0")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="sas_ttl_minutes"):
        Settings()
