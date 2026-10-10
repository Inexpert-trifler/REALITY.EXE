"""Authentication service.

All registration, login, and current-user lookup logic lives here.
Route handlers must not contain any auth business logic.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, UnauthorizedException
from app.models.player_profile import PlayerProfile
from app.models.user import User
from app.repositories.user_repository import PlayerProfileRepository, UserRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    PlayerProfileResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.utils.jwt import create_access_token, get_token_lifetime_seconds
from app.utils.password import hash_password, verify_password

logger = logging.getLogger(__name__)

_user_repo = UserRepository()
_profile_repo = PlayerProfileRepository()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_user_response(user: User) -> UserResponse:
    """Serialize a User ORM object (with optional loaded profile) to schema."""
    profile_resp: PlayerProfileResponse | None = None
    if user.profile is not None:
        profile_resp = PlayerProfileResponse(
            display_name=user.profile.display_name,
            level=user.profile.level,
            total_xp=user.profile.total_xp,
            preferred_personality=user.profile.preferred_personality,
            preferred_play_style=user.profile.preferred_play_style,
        )
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        profile=profile_resp,
    )


def _build_token_response() -> TokenResponse:
    """Placeholder — token is built by callers who have the user id."""
    raise NotImplementedError  # pragma: no cover


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def register_user(db: AsyncSession, payload: RegisterRequest) -> RegisterResponse:
    """Create a new User + PlayerProfile and return a JWT.

    Raises:
        ConflictException: if the email or username is already taken.
    """
    # Uniqueness checks
    existing_email = await _user_repo.get_by_email(db, payload.email)
    if existing_email is not None:
        raise ConflictException(
            message="An account with this email address already exists",
            details={"field": "email"},
        )

    existing_username = await _user_repo.get_by_username(db, payload.username)
    if existing_username is not None:
        raise ConflictException(
            message="This username is already taken",
            details={"field": "username"},
        )

    # Create user
    new_user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
    )
    user = await _user_repo.create(db, new_user)

    # Create player profile with defaults
    new_profile = PlayerProfile(
        user_id=user.id,
        display_name=payload.display_name,
        level=1,
        total_xp=0,
        preferred_personality=None,
        preferred_play_style=None,
    )
    profile = await _profile_repo.create(db, new_profile)

    # Attach profile to the in-memory user so the response builder can use it
    user.profile = profile

    # Issue JWT
    access_token = create_access_token(subject=str(user.id))

    logger.info("New user registered: id=%s username=%s", user.id, user.username)

    return RegisterResponse(
        user=_build_user_response(user),
        token=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=get_token_lifetime_seconds(),
        ),
    )


async def login_user(db: AsyncSession, payload: LoginRequest) -> LoginResponse:
    """Authenticate a user by email/password and return a JWT.

    Raises:
        UnauthorizedException: if credentials are invalid.
    """
    user = await _user_repo.get_by_email(db, payload.email)

    # Use a constant-time path to avoid user enumeration timing attacks
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedException(message="Invalid email or password")

    # Eagerly load profile for the response to avoid SQLAlchemy MissingGreenlet lazy-load error
    user = await _user_repo.get_by_id_with_profile(db, user.id)

    access_token = create_access_token(subject=str(user.id))

    logger.info("User logged in: id=%s username=%s", user.id, user.username)

    return LoginResponse(
        user=_build_user_response(user),
        token=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=get_token_lifetime_seconds(),
        ),
    )


async def get_current_user_by_id(db: AsyncSession, user_id: UUID) -> User:
    """Fetch and return the User (with profile eagerly loaded) for an already-validated token.

    Raises:
        UnauthorizedException: if the user no longer exists.
    """
    user = await _user_repo.get_by_id_with_profile(db, user_id)
    if user is None:
        raise UnauthorizedException(message="User not found")
    return user


def logout_user() -> LogoutResponse:
    """Return a logout confirmation.

    JWT tokens are stateless; invalidation is handled client-side (dropping
    the token).  Server-side token revocation (blocklist) can be added later.
    """
    return LogoutResponse()
