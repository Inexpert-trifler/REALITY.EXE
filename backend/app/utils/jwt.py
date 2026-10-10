"""JWT token creation and decoding utilities.

Provides a thin, typed wrapper around core security functions so the
service and dependency layers never import JWT libraries directly.
"""

from datetime import timedelta
from typing import Any

import jwt

from app.core.config import get_settings
from app.core.security import create_access_token as _create_access_token
from app.core.security import decode_access_token as _decode_access_token


class TokenError(Exception):
    """Raised when a JWT cannot be decoded or has expired."""


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Issue a signed JWT for *subject* (user id string).

    Expiration is driven by ``ACCESS_TOKEN_EXPIRE_MINUTES`` in settings.
    """
    return _create_access_token(subject=subject, extra_claims=extra_claims)


def create_access_token_with_expiry(
    subject: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Issue a JWT with an explicit expiry delta (useful for testing short-lived tokens)."""
    return _create_access_token(
        subject=subject, expires_delta=expires_delta, extra_claims=extra_claims
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT.

    Raises:
        TokenError: if the token is malformed, expired, or has an invalid
                    signature.
    """
    try:
        return _decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError(f"Invalid token: {exc}") from exc


def get_token_lifetime_seconds() -> int:
    """Return the configured access-token lifetime in seconds."""
    return get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60
