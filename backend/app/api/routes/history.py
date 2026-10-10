"""Quest history route handlers."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.db.session import get_db
from app.schemas.errors import AUTH_RESPONSES, Error403, Error404
from app.schemas.history import AttemptHistoryItem, QuestHistoryResponse
from app.services import history_service

router = APIRouter(prefix="/history", tags=["History"])


@router.get(
    "",
    response_model=QuestHistoryResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Get the authenticated player's quest history",
    responses={
        200: {"description": "Paginated quest attempt history"},
        **AUTH_RESPONSES,
    },
)
async def get_history(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=20, ge=1, le=50, description="Page size (max 50)"),
    status: str | None = Query(
        default=None,
        description="Filter by attempt status: `COMPLETED` · `ABANDONED` · `ACTIVE` etc.",
    ),
    sort_by: Literal["started_at", "completed_at", "earned_xp"] = Query(
        default="started_at",
        description="Field to sort by",
    ),
    sort_dir: Literal["asc", "desc"] = Query(
        default="desc",
        description="Sort direction",
    ),
) -> QuestHistoryResponse:
    """Return a paginated log of all the player's quest attempts.

    Each history item includes:
    - Quest title, difficulty, play style, and duration
    - Attempt status and earned XP
    - Whether Pocket Mode was used
    - Evidence count and latest AI analysis outcome

    All results are scoped strictly to the authenticated player.

    **Requires**: `Authorization: Bearer <token>`
    """
    return await history_service.get_history(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status_filter=status,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get(
    "/{attempt_id}",
    response_model=AttemptHistoryItem,
    status_code=http_status.HTTP_200_OK,
    summary="Get detail for a single quest attempt",
    responses={
        200: {"description": "Full attempt detail including evidence summary"},
        403: {"model": Error403, "description": "Attempt belongs to another player"},
        404: {"model": Error404, "description": "Quest attempt not found"},
        **AUTH_RESPONSES,
    },
)
async def get_attempt_detail(
    attempt_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AttemptHistoryItem:
    """Return full detail for a single quest attempt.

    Includes the complete attempt record plus an evidence summary showing
    how many photos were uploaded and what the AI analysis concluded.

    Returns `403 Forbidden` if the attempt belongs to another player.

    **Requires**: `Authorization: Bearer <token>`
    """
    return await history_service.get_attempt_detail(
        db,
        user_id=current_user.id,
        attempt_id=attempt_id,
    )
