"""JWT mock validation for POC upload endpoints."""

from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import ExpiredSignatureError
from jwt.exceptions import InvalidTokenError as JwtDecodeError

from config import Settings, get_settings

BEARER_PREFIX = "Bearer "
JWT_ALGORITHM = "HS256"


class AuthenticationError(Exception):
    """Base authentication error."""


class MissingAuthorizationError(AuthenticationError):
    """Authorization header is missing."""


class InvalidAuthorizationFormatError(AuthenticationError):
    """Authorization header is malformed."""


class InvalidTokenError(AuthenticationError):
    """JWT is invalid or cannot be verified."""


class ExpiredTokenError(AuthenticationError):
    """JWT has expired."""


class AuthConfigurationError(AuthenticationError):
    """Auth service is misconfigured."""


def extract_bearer_token(authorization_header: str | None) -> str:
    """Extract the Bearer token from an Authorization header value."""
    if not authorization_header:
        raise MissingAuthorizationError("Authorization header is required")

    if not authorization_header.startswith(BEARER_PREFIX):
        raise InvalidAuthorizationFormatError(
            "Authorization header must use Bearer scheme",
        )

    token = authorization_header.removeprefix(BEARER_PREFIX).strip()
    if not token:
        raise InvalidAuthorizationFormatError("Bearer token is empty")

    return token


def validate_jwt(token: str, settings: Settings | None = None) -> str:
    """Validate a JWT mock token and return the authenticated user id."""
    resolved_settings = settings or get_settings()
    if not resolved_settings.jwt_mock_secret:
        raise AuthConfigurationError("JWT_MOCK_SECRET is not configured")

    try:
        payload = jwt.decode(
            token,
            resolved_settings.jwt_mock_secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
    except ExpiredSignatureError as exc:
        raise ExpiredTokenError("JWT has expired") from exc
    except JwtDecodeError as exc:
        raise InvalidTokenError("JWT is invalid") from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise InvalidTokenError("JWT subject is missing or invalid")

    return user_id


def authenticate_request(
    authorization_header: str | None,
    settings: Settings | None = None,
) -> str:
    """Validate an Authorization header and return the authenticated user id."""
    token = extract_bearer_token(authorization_header)
    return validate_jwt(token, settings=settings)


def create_mock_token(
    user_id: str,
    secret: str,
    *,
    expires_in_seconds: int = 3600,
    issued_at: datetime | None = None,
) -> str:
    """Create a signed JWT mock token for tests and local development."""
    issued = issued_at or datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iat": issued,
        "exp": issued + timedelta(seconds=expires_in_seconds),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)
