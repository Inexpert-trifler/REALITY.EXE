"""Reflection route handlers."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_text_provider
from app.db.session import get_db
from app.schemas.errors import AUTH_RESPONSES, Error400, Error403, Error404
from app.schemas.reflection import (
    ReflectionCreateRequest,
    ReflectionListResponse,
    ReflectionResponse,
)
from app.services import reflection_service

router = APIRouter(prefix="/reflections", tags=["Reflections"])


@router.post(
    "",
    response_model=ReflectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a Game Master reflection for a completed quest",
    responses={
        201: {"description": "Reflection generated and persisted"},
        400: {
            "model": Error400,
            "description": "Attempt is not in a terminal state (COMPLETED or ABANDONED)",
        },
        403: {"model": Error403, "description": "Attempt belongs to another player"},
        404: {"model": Error404, "description": "Quest attempt not found"},
        **AUTH_RESPONSES,
    },
)
async def create_reflection(
    payload: ReflectionCreateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    text_provider=Depends(get_text_provider),
    x_idempotency_key: str | None = Header(
        default=None,
        alias="X-Idempotency-Key",
        description="Optional idempotency key for offline-first clients",
    ),
) -> ReflectionResponse:
    """Generate a personalised in-character reflection from the Game Master.

    The attempt must be in a **terminal** state — `COMPLETED` or `ABANDONED`.

    The reflection is structured in three parts:
    - **reflection**: 2–3 sentences acknowledging what happened (never shaming)
    - **gm_message**: optional in-character personal note from the Game Master
    - **next_quest_suggestion**: optional teaser for the player's next adventure

    Falls back to a curated hand-crafted template if AI is unavailable.

    The response includes `sync` metadata for offline-first clients.
    Optionally supply `X-Idempotency-Key` and it will be echoed back.

    **Requires**: `Authorization: Bearer <token>`
    """
    return await reflection_service.create_reflection(
        db,
        user_id=current_user.id,
        attempt_id=UUID(payload.attempt_id),
        text_provider=text_provider,
        idempotency_key=x_idempotency_key,
    )


@router.get(
    "",
    response_model=ReflectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all reflections for the authenticated player",
    responses={
        200: {"description": "Paginated list of reflections, newest first"},
        **AUTH_RESPONSES,
    },
)
async def list_reflections(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=20, ge=1, le=50, description="Page size (max 50)"),
) -> ReflectionListResponse:
    """Return all reflections for the authenticated player, newest first.

    List items have `sync: null` — sync metadata is only included on creation.

    **Requires**: `Authorization: Bearer <token>`
    """
    return await reflection_service.list_reflections(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
