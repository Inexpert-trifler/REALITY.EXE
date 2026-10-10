"""Quest completion and evidence analysis route handlers."""

import logging
from uuid import UUID

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_text_provider
from app.db.session import get_db
from app.schemas.chaos import ChaosNextRequest, ChaosNextResponse
from app.schemas.completion import AnalysisResultResponse, CompletionResponse
from app.schemas.errors import (
    AUTH_RESPONSES,
    Error400,
    Error403,
    Error404,
    Error422,
)
from app.services import completion_service, verification_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Vision provider dependency
# ---------------------------------------------------------------------------


def get_vision_provider():
    """Return the configured vision provider (Ollama in production)."""
    from app.core.config import get_settings

    settings = get_settings()

    if settings.ENVIRONMENT == "test":
        from tests.fakes.fake_provider import FakeVisionProvider

        return FakeVisionProvider()

    from app.ai.providers.ollama_provider import OllamaVisionProvider

    return OllamaVisionProvider()


# ---------------------------------------------------------------------------
# Evidence analysis — tagged AI
# ---------------------------------------------------------------------------


@router.post(
    "/evidence/{evidence_id}/analyze",
    response_model=AnalysisResultResponse,
    status_code=status.HTTP_200_OK,
    tags=["AI"],
    summary="Analyse evidence with the AI vision judge",
    responses={
        200: {"description": "Analysis result with outcome and confidence"},
        400: {"model": Error400, "description": "Evidence does not belong to an active attempt"},
        403: {"model": Error403, "description": "Evidence belongs to another player"},
        404: {"model": Error404, "description": "Evidence not found"},
        422: {"model": Error422, "description": "Image body too large (max 11 MB) or invalid"},
        **AUTH_RESPONSES,
    },
)
async def analyze_evidence(
    evidence_id: UUID,
    current_user: CurrentUser,
    image_bytes: bytes = Body(
        ...,
        media_type="application/octet-stream",
        description="Raw image bytes of the evidence to analyse (max 11 MB)",
        max_length=11 * 1024 * 1024,
    ),
    db: AsyncSession = Depends(get_db),
    vision_provider=Depends(get_vision_provider),
) -> AnalysisResultResponse:
    """Submit the raw image bytes of uploaded evidence for AI vision analysis.

    The AI judges whether the image supports quest completion and returns
    one of four outcomes:

    | Outcome | Meaning | Next action |
    |---|---|---|
    | `SUCCESS` | Evidence supports completion | Call `POST /quests/{id}/complete` |
    | `INCOMPLETE` | Evidence insufficient | Re-upload a clearer photo |
    | `UNCERTAIN` | Low model confidence | Retry analysis |
    | `UNSAFE` | Safety concerns detected | Completion blocked |

    Send the raw image bytes as `application/octet-stream` in the request body
    (not as multipart — the evidence was uploaded separately via `/evidence/upload`).

    **Requires**: `Authorization: Bearer <token>`
    """
    return await verification_service.analyze_evidence(
        db,
        evidence_id=evidence_id,
        user_id=current_user.id,
        vision_provider=vision_provider,
        image_bytes=image_bytes,
    )


# ---------------------------------------------------------------------------
# Quest completion — tagged Quests
# ---------------------------------------------------------------------------


@router.post(
    "/quests/{quest_id}/complete",
    response_model=CompletionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Quests"],
    summary="Complete a quest and collect XP  (VERIFYING → COMPLETED)",
    responses={
        200: {"description": "Quest completed; XP awarded, achievements evaluated"},
        400: {"model": Error400, "description": "Attempt is not in VERIFYING state"},
        404: {"model": Error404, "description": "No attempt found for this quest"},
        **AUTH_RESPONSES,
    },
)
async def complete_quest(
    quest_id: UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    text_provider=Depends(get_text_provider),
) -> CompletionResponse:
    """Finalise a quest attempt and collect the XP reward.

    The attempt **must** be in `VERIFYING` state (evidence has been analysed
    with a `SUCCESS` outcome).

    On success:
    - Attempt transitions to `COMPLETED`
    - XP is awarded (idempotent — calling twice won't double-award)
    - Level is recalculated
    - New achievements are evaluated and unlocked
    - A personalised AI reflection is generated

    The response includes all side-effects in a single payload so the client
    can render a rich end-screen without extra round-trips.

    **Requires**: `Authorization: Bearer <token>`
    """
    return await completion_service.complete_quest(
        db,
        user_id=current_user.id,
        quest_id=quest_id,
        text_provider=text_provider,
    )


# ---------------------------------------------------------------------------
# Chaos Mode — tagged Quests
# ---------------------------------------------------------------------------


@router.post(
    "/quests/{attempt_id}/chaos-next",
    response_model=ChaosNextResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Quests"],
    summary="Generate the next quest in a Chaos chain",
    responses={
        201: {"description": "Continuation quest generated; new attempt started"},
        400: {
            "model": Error400,
            "description": "Attempt not COMPLETED, or chain has reached maximum depth",
        },
        403: {"model": Error403, "description": "Attempt belongs to another player"},
        404: {"model": Error404, "description": "Attempt not found"},
        422: {"model": Error422, "description": "discovery_context too short or duration invalid"},
        **AUTH_RESPONSES,
    },
)
async def chaos_next(
    attempt_id: UUID,
    payload: ChaosNextRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    text_provider=Depends(get_text_provider),
) -> ChaosNextResponse:
    """Generate a Chaos Mode continuation quest.

    After completing a quest, describe what you discovered and the AI
    Game Master will generate the next mission building on that discovery.

    The continuation quest passes the same full safety validation pipeline.
    The chain is capped at `CHAOS_MAX_CHAIN_DEPTH` (default 5) to prevent
    unbounded missions.

    **Idempotent** — calling this twice for the same completed attempt returns
    the existing continuation without regenerating.

    **Requires**: `Authorization: Bearer <token>`
    """
    from app.services.chaos_service import generate_chaos_next

    return await generate_chaos_next(
        db,
        user_id=current_user.id,
        completed_attempt_id=attempt_id,
        discovery_context=payload.discovery_context,
        duration_minutes=payload.duration_minutes,
        text_provider=text_provider,
    )
