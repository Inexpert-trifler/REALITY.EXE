"""Quest route handlers."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestrator import QuestOrchestrator
from app.ai.schemas.quest_output import QuestGenerateRequest
from app.api.dependencies import CurrentUser, get_text_provider
from app.db.session import get_db
from app.repositories.quest_repository import QuestAttemptRepository
from app.schemas.errors import (
    AUTH_RESPONSES,
    Error400,
    Error404,
    Error422,
)
from app.schemas.quest import AttemptResponse, QuestListResponse, QuestResponse
from app.services import quest_service

_attempt_repo = QuestAttemptRepository()

router = APIRouter(prefix="/quests", tags=["Quests"])


@router.get(
    "",
    response_model=QuestListResponse,
    status_code=status.HTTP_200_OK,
    summary="List available quests",
    responses={
        200: {"description": "Paginated list of quests"},
        **AUTH_RESPONSES,
    },
)
async def list_quests(
    _current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Number of records to skip (pagination offset)"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return (1–100)"),
) -> QuestListResponse:
    """Return a paginated list of all available quests.

    Use `skip` and `limit` for pagination.

    **Requires**: `Authorization: Bearer <token>`
    """
    return await quest_service.list_quests(db, skip=skip, limit=limit)


@router.post(
    "/generate",
    response_model=QuestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new quest using the AI Game Master",
    responses={
        201: {"description": "Quest generated and ready to start"},
        422: {"model": Error422, "description": "Invalid difficulty, environment, or personality"},
        **AUTH_RESPONSES,
    },
)
async def generate_quest(
    payload: QuestGenerateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    provider=Depends(get_text_provider),
) -> QuestResponse:
    """Generate a personalised quest using the AI pipeline.

    The AI Game Master considers your chosen personality, environment,
    difficulty, and play style to create a unique real-world mission.
    All generated quests pass the full safety and quality validation pipeline.

    Falls back to a curated hand-crafted quest if AI generation fails.

    | Parameter | Options |
    |---|---|
    | `duration_minutes` | 5–120 |
    | `environment` | `campus` · `park` · `neighborhood` · `trail` · `city` · `any` |
    | `difficulty` | `chill` · `curious` · `explorer` · `chaos` |
    | `play_style` | `explorer` · `detective` · `observer` · `adventurer` · `chaos` |
    | `personality` | `Wizard` · `Rogue AI` · `Captain` · `Sensei` · `Alien` |

    **Requires**: `Authorization: Bearer <token>`
    """
    player_level = 1
    previous_titles: list[str] = []
    if current_user.profile is not None:
        player_level = current_user.profile.level
    orchestrator = QuestOrchestrator(provider=provider)
    return await orchestrator.generate(
        db=db,
        request=payload,
        player_level=player_level,
        previous_quest_titles=previous_titles,
    )


@router.get(
    "/{quest_id}",
    response_model=QuestResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a quest by ID",
    responses={
        200: {"description": "Quest details"},
        404: {"model": Error404, "description": "Quest not found"},
        **AUTH_RESPONSES,
    },
)
async def get_quest(
    quest_id: UUID,
    _current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> QuestResponse:
    """Return the full details for a single quest by its UUID.

    **Requires**: `Authorization: Bearer <token>`
    """
    return await quest_service.get_quest(db, quest_id)


@router.post(
    "/{quest_id}/start",
    response_model=AttemptResponse,
    status_code=status.HTTP_200_OK,
    summary="Start a quest  (CREATED → ACTIVE)",
    responses={
        200: {"description": "Attempt created and set to ACTIVE"},
        400: {"model": Error400, "description": "Player already has an active quest attempt"},
        404: {"model": Error404, "description": "Quest not found"},
        **AUTH_RESPONSES,
    },
)
async def start_quest(
    quest_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AttemptResponse:
    """Start a quest attempt.

    A new attempt is implicitly created and transitioned to **ACTIVE**.
    Returns `400` if the player already has a non-terminal attempt on
    another quest — only one active quest at a time is permitted.

    **Requires**: `Authorization: Bearer <token>`
    """
    return await quest_service.start_attempt(db, current_user.id, quest_id)


@router.post(
    "/{quest_id}/pocket",
    response_model=AttemptResponse,
    status_code=status.HTTP_200_OK,
    summary="Enter Pocket Mode  (ACTIVE → POCKET_MODE)",
    responses={
        200: {"description": "Attempt transitioned to POCKET_MODE"},
        400: {"model": Error400, "description": "Invalid state transition"},
        404: {"model": Error404, "description": "No active attempt found for this quest"},
        **AUTH_RESPONSES,
    },
)
async def enter_pocket_mode(
    quest_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AttemptResponse:
    """Switch the attempt to **Pocket Mode**.

    The player should put their phone away and go complete the mission.
    The UI should display only the minimum information needed.

    Valid from: `ACTIVE`

    **Requires**: `Authorization: Bearer <token>`
    """
    return await quest_service.enter_pocket_mode(db, current_user.id, quest_id)


@router.post(
    "/{quest_id}/return",
    response_model=AttemptResponse,
    status_code=status.HTTP_200_OK,
    summary="Return from Pocket Mode  (POCKET_MODE → RETURNED)",
    responses={
        200: {"description": "Attempt transitioned to RETURNED"},
        400: {"model": Error400, "description": "Invalid state transition"},
        404: {"model": Error404, "description": "No active attempt found for this quest"},
        **AUTH_RESPONSES,
    },
)
async def return_from_pocket_mode(
    quest_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AttemptResponse:
    """Signal that the player has returned from the field.

    After this call, the player should upload evidence to proceed.

    Valid from: `POCKET_MODE`

    **Requires**: `Authorization: Bearer <token>`
    """
    return await quest_service.return_from_pocket_mode(db, current_user.id, quest_id)


@router.post(
    "/{quest_id}/pause",
    response_model=AttemptResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause the active quest  (ACTIVE → PAUSED)",
    responses={
        200: {"description": "Attempt paused"},
        400: {"model": Error400, "description": "Invalid state transition"},
        404: {"model": Error404, "description": "No active attempt found for this quest"},
        **AUTH_RESPONSES,
    },
)
async def pause_quest(
    quest_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AttemptResponse:
    """Pause an active quest without abandoning it.

    The attempt can be resumed later via `/resume`.

    Valid from: `ACTIVE`

    **Requires**: `Authorization: Bearer <token>`
    """
    return await quest_service.pause_attempt(db, current_user.id, quest_id)


@router.post(
    "/{quest_id}/resume",
    response_model=AttemptResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume a paused quest  (PAUSED → ACTIVE)",
    responses={
        200: {"description": "Attempt resumed and set to ACTIVE"},
        400: {"model": Error400, "description": "Invalid state transition"},
        404: {"model": Error404, "description": "No active attempt found for this quest"},
        **AUTH_RESPONSES,
    },
)
async def resume_quest(
    quest_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AttemptResponse:
    """Resume a previously paused quest attempt.

    Valid from: `PAUSED`

    **Requires**: `Authorization: Bearer <token>`
    """
    return await quest_service.resume_attempt(db, current_user.id, quest_id)


@router.post(
    "/{quest_id}/abandon",
    response_model=AttemptResponse,
    status_code=status.HTTP_200_OK,
    summary="Abandon the current quest attempt",
    responses={
        200: {"description": "Attempt abandoned; no XP awarded"},
        400: {"model": Error400, "description": "Invalid state transition (already terminal)"},
        404: {"model": Error404, "description": "No active attempt found for this quest"},
        **AUTH_RESPONSES,
    },
)
async def abandon_quest(
    quest_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AttemptResponse:
    """Abandon a live quest attempt.

    No XP is awarded.  The game will not shame you — quitting is always
    an option.  You can start the same or a different quest afterwards.

    Valid from: `CREATED` · `ACTIVE` · `POCKET_MODE` · `RETURNED` ·
    `EVIDENCE_PENDING` · `PAUSED`

    **Requires**: `Authorization: Bearer <token>`
    """
    return await quest_service.abandon_attempt(db, current_user.id, quest_id)
