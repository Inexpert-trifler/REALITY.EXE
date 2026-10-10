"""FastAPI dependency providers for authentication, authorization, and AI.

Import these in route modules — never place auth or AI logic inside route handlers.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedException
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_current_user_by_id
from app.utils.jwt import TokenError, decode_access_token

logger = logging.getLogger(__name__)

# HTTPBearer extracts the token from the "Authorization: Bearer <token>" header.
# auto_error=False lets us return a custom 401 instead of the default FastAPI one.
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db=Depends(get_db),
) -> User:
    """Validate the Bearer token and return the authenticated User."""
    if credentials is None:
        raise UnauthorizedException(message="Authentication credentials were not provided")

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        logger.debug("Token validation failed: %s", exc)
        raise UnauthorizedException(message=str(exc)) from exc

    subject: str | None = payload.get("sub")
    if subject is None:
        raise UnauthorizedException(message="Token payload is missing subject claim")

    try:
        user_id = UUID(subject)
    except ValueError:
        raise UnauthorizedException(message="Token subject is not a valid user identifier")

    user = await get_current_user_by_id(db, user_id)
    return user


# Typed alias for injection in route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# AI provider dependency
# ---------------------------------------------------------------------------


def get_text_provider():
    """Return the production Ollama text provider.

    This function is the single place where the concrete provider is
    chosen.  Tests override this dependency with a fake provider — the
    fake must NEVER leak into production code paths.
    """
    from app.ai.providers.ollama_provider import OllamaTextProvider

    settings = get_settings()


    return OllamaTextProvider(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.TEXT_MODEL,
        timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
        temperature=settings.AI_GENERATION_TEMPERATURE,
        max_retries=settings.AI_MAX_RETRIES,
    )


TextProvider = Annotated[object, Depends(get_text_provider)]


# ---------------------------------------------------------------------------
# Storage provider dependency
# ---------------------------------------------------------------------------


def get_storage_provider():
    """Return the configured storage provider.

    Tests override this with an in-memory fake — the real provider must
    never be used in tests that don't need actual file I/O.
    """
    from app.storage.local_storage import LocalStorageProvider

    return LocalStorageProvider()


StorageProviderDep = Annotated[object, Depends(get_storage_provider)]
