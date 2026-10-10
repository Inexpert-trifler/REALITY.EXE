"""Achievement route handlers."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.db.session import get_db
from app.schemas.achievement import AchievementListResponse
from app.schemas.errors import AUTH_RESPONSES
from app.services import achievement_service

router = APIRouter(prefix="/achievements", tags=["Achievements"])


@router.get(
    "",
    response_model=AchievementListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the authenticated player's achievement catalogue",
    responses={
        200: {"description": "Full achievement catalogue with unlock status"},
        **AUTH_RESPONSES,
    },
)
async def get_achievements(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AchievementListResponse:
    """Return the complete achievement catalogue for the authenticated player.

    Both **locked** and **unlocked** achievements are returned.
    Locked achievements have `unlocked_at: null`.

    | Achievement | Condition |
    |---|---|
    | `first_contact` | Complete your very first quest |
    | `touch_grass` | Complete 3 outdoor quests |
    | `curious_mind` | Complete 5 Observer quests |
    | `chaos_agent` | Complete a Chaos quest |
    | `pocket_player` | Complete 5 quests using Pocket Mode |

    **Requires**: `Authorization: Bearer <token>`
    """
    return await achievement_service.get_user_achievements(db, current_user.id)
