"""Player profile and progression route handlers."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.db.session import get_db
from app.schemas.errors import AUTH_RESPONSES, Error422
from app.schemas.player import PlayerStatsResponse, ProfilePatchRequest, ProfileResponse
from app.services import player_service

router = APIRouter(prefix="/player", tags=["Player"])


@router.get(
    "/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the authenticated player's profile",
    responses={
        200: {"description": "Player profile"},
        **AUTH_RESPONSES,
    },
)
async def get_profile(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Return the authenticated player's display name, personality preference,
    play-style preference, current level, and total XP.

    **Requires**: `Authorization: Bearer <token>`
    """
    return await player_service.get_profile(db, current_user.id)


@router.patch(
    "/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update the authenticated player's profile",
    responses={
        200: {"description": "Updated player profile"},
        422: {"model": Error422, "description": "Invalid personality or play style value"},
        **AUTH_RESPONSES,
    },
)
async def patch_profile(
    payload: ProfilePatchRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Update one or more editable profile fields.

    All fields are **optional** — omit any field you don't want to change.

    | Field | Values |
    |---|---|
    | `display_name` | 1–100 chars |
    | `preferred_personality` | `Wizard` · `Rogue AI` · `Captain` · `Sensei` · `Alien` |
    | `preferred_play_style` | `explorer` · `detective` · `observer` · `adventurer` · `chaos` |

    **XP and level cannot be modified here.**

    **Requires**: `Authorization: Bearer <token>`
    """
    return await player_service.patch_profile(db, current_user.id, payload)


@router.get(
    "/stats",
    response_model=PlayerStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the authenticated player's gameplay statistics",
    responses={
        200: {"description": "Aggregated player statistics"},
        **AUTH_RESPONSES,
    },
)
async def get_stats(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PlayerStatsResponse:
    """Return aggregated statistics for the authenticated player.

    Includes:
    - Quest counts (total, completed, abandoned) and completion rate
    - Current level, total XP, and level-progress breakdown
    - Achievement count
    - Favourite play style and average quest duration (computed from history)

    **Requires**: `Authorization: Bearer <token>`
    """
    return await player_service.get_stats(db, current_user.id)
