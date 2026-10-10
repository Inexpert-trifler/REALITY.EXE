"""Authentication route handlers."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from app.schemas.errors import (
    AUTH_RESPONSES,
    Error401,
    Error409,
    Error422,
)
from app.services import auth_service
from app.services.auth_service import _build_user_response

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new player account",
    responses={
        201: {"description": "Account created successfully; token returned"},
        409: {"model": Error409, "description": "Email or username already in use"},
        422: {
            "model": Error422,
            "description": "Validation failed (weak password, bad email, etc.)",
        },
    },
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Create a new player account.

    - **username**: 3–30 chars, letters/numbers/underscores/hyphens only
    - **email**: valid email address (normalised to lowercase)
    - **password**: ≥8 chars, must contain a letter and a digit
    - **display_name**: 1–100 chars shown in-game

    Returns a **JWT access token** valid for 60 minutes alongside the
    new user record and their initialised player profile (level 1, 0 XP).
    """
    return await auth_service.register_user(db, payload)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in and receive an access token",
    responses={
        200: {"description": "Login successful; access token returned"},
        401: {"model": Error401, "description": "Invalid email or password"},
        422: {"model": Error422, "description": "Malformed request body"},
    },
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Authenticate with **email** and **password**.

    Returns a **JWT Bearer token** on success.  Returns `401 Unauthorized`
    for invalid credentials — the error message is deliberately vague to
    prevent user enumeration.
    """
    return await auth_service.login_user(db, payload)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Sign out (invalidate client-side token)",
    responses={
        200: {"description": "Logout acknowledged"},
        **AUTH_RESPONSES,
    },
)
async def logout(
    _current_user: CurrentUser,
) -> LogoutResponse:
    """Signal that the player has logged out.

    JWT tokens are stateless — the client must discard the token.
    This endpoint requires a valid token so stale tokens cannot
    produce a false confirmation.

    **Requires**: `Authorization: Bearer <token>`
    """
    return auth_service.logout_user()


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the currently authenticated user",
    responses={
        200: {"description": "Authenticated user record"},
        **AUTH_RESPONSES,
    },
)
async def me(current_user: CurrentUser) -> UserResponse:
    """Return the currently authenticated user and their player profile.

    **Requires**: `Authorization: Bearer <token>`
    """
    return _build_user_response(current_user)
