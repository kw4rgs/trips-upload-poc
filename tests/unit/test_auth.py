"""Unit tests for JWT mock authentication service."""

from datetime import UTC, datetime, timedelta

import pytest

from services.auth import (
    AuthConfigurationError,
    ExpiredTokenError,
    InvalidAuthorizationFormatError,
    InvalidTokenError,
    MissingAuthorizationError,
    authenticate_request,
    create_mock_token,
    extract_bearer_token,
    validate_jwt,
)


def test_extract_bearer_token_returns_token() -> None:
    token = extract_bearer_token("Bearer abc.def.ghi")
    assert token == "abc.def.ghi"


def test_extract_bearer_token_requires_header() -> None:
    with pytest.raises(MissingAuthorizationError):
        extract_bearer_token(None)


def test_extract_bearer_token_requires_bearer_scheme() -> None:
    with pytest.raises(InvalidAuthorizationFormatError):
        extract_bearer_token("Token abc.def.ghi")


def test_validate_jwt_returns_user_id(settings) -> None:
    token = create_mock_token("user-123", settings.jwt_mock_secret)
    assert validate_jwt(token, settings=settings) == "user-123"


def test_validate_jwt_rejects_invalid_signature(settings) -> None:
    token = create_mock_token("user-123", "wrong-secret-thirty-two-characters!")
    with pytest.raises(InvalidTokenError):
        validate_jwt(token, settings=settings)


def test_validate_jwt_rejects_expired_token(settings) -> None:
    issued_at = datetime.now(UTC) - timedelta(hours=2)
    token = create_mock_token(
        "user-123",
        settings.jwt_mock_secret,
        expires_in_seconds=-3600,
        issued_at=issued_at,
    )
    with pytest.raises(ExpiredTokenError):
        validate_jwt(token, settings=settings)


def test_validate_jwt_requires_secret(settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_MOCK_SECRET", raising=False)
    settings.jwt_mock_secret = ""
    token = create_mock_token("user-123", "test-secret-thirty-two-characters-long!")
    with pytest.raises(AuthConfigurationError):
        validate_jwt(token, settings=settings)


def test_authenticate_request_validates_authorization_header(settings) -> None:
    token = create_mock_token("user-456", settings.jwt_mock_secret)
    user_id = authenticate_request(f"Bearer {token}", settings=settings)
    assert user_id == "user-456"
