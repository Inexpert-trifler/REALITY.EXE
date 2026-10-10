"""ReflectionService — generates and persists personalised quest reflections.

Pipeline:
  1. Load QuestAttempt + Quest + player context.
  2. Build rich ReflectionRequest.
  3. Call TextModelProvider.generate_reflection().
  4. Parse the three-section response (REFLECTION / GM_MESSAGE / NEXT_QUEST).
  5. If provider unavailable or output unusable, fall back to deterministic templates.
  6. Persist Reflection record (text stored as structured sentinel-delimited string).
  7. Return ReflectionResponse.

Storage format (opaque to the DB, parsed by this service):
    <reflection text>|||<gm_message>|||<next_quest_suggestion>|||<is_fallback:0|1>

Existing callers that used the simple text field see the first segment only;
the service always parses the full record when serving ReflectionResponse.

The prompt instructs the model to produce three labelled sections:
    REFLECTION: ...
    GM_MESSAGE: ...
    NEXT_QUEST: ...

If any section is missing, a sensible default is substituted.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import ReflectionRequest, TextModelProvider
from app.ai.reflection_fallbacks import FallbackReflection, get_fallback
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt
from app.models.reflection import Reflection
from app.repositories.reflection_repository import ReflectionRepository
from app.schemas.reflection import ReflectionListResponse, ReflectionResponse
from app.schemas.sync import SyncMetadata

logger = logging.getLogger(__name__)

_reflection_repo = ReflectionRepository()

# Sentinel used to pack all parts into the text column
_SEP = "|||"

# Label prefixes the model is asked to use
_LABEL_REFLECTION = "REFLECTION:"
_LABEL_GM = "GM_MESSAGE:"
_LABEL_NEXT = "NEXT_QUEST:"

FALLBACK_MODEL_NAME = "fallback-templates"


# ---------------------------------------------------------------------------
# Structured text packing / unpacking
# ---------------------------------------------------------------------------


def _pack(text: str, gm_message: str, next_quest: str, is_fallback: bool) -> str:
    """Serialise all four fields into a single string for DB storage."""
    flag = "1" if is_fallback else "0"
    return _SEP.join([text, gm_message, next_quest, flag])


def _unpack(stored: str) -> tuple[str, str | None, str | None, bool]:
    """Deserialise a stored reflection string.

    Returns (text, gm_message, next_quest_suggestion, is_fallback).
    Handles legacy records that contain no sentinel.
    """
    parts = stored.split(_SEP, 3)
    if len(parts) == 4:
        return parts[0], parts[1] or None, parts[2] or None, parts[3] == "1"
    # Legacy / plain text record
    return stored, None, None, False


# ---------------------------------------------------------------------------
# Model output parser
# ---------------------------------------------------------------------------


def _parse_model_output(raw_text: str) -> tuple[str, str, str]:
    """Extract the three labelled sections from the model's plain-text output.

    Returns (reflection, gm_message, next_quest).
    Each defaults to a safe empty string if the label is absent.
    """
    reflection = ""
    gm_message = ""
    next_quest = ""

    current_label: str | None = None
    buffer: list[str] = []

    def _flush() -> None:
        nonlocal reflection, gm_message, next_quest
        value = " ".join(buffer).strip()
        if current_label == _LABEL_REFLECTION:
            reflection = value
        elif current_label == _LABEL_GM:
            gm_message = value
        elif current_label == _LABEL_NEXT:
            next_quest = value

    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(_LABEL_REFLECTION):
            _flush()
            buffer = [stripped[len(_LABEL_REFLECTION) :].strip()]
            current_label = _LABEL_REFLECTION
        elif stripped.startswith(_LABEL_GM):
            _flush()
            buffer = [stripped[len(_LABEL_GM) :].strip()]
            current_label = _LABEL_GM
        elif stripped.startswith(_LABEL_NEXT):
            _flush()
            buffer = [stripped[len(_LABEL_NEXT) :].strip()]
            current_label = _LABEL_NEXT
        elif current_label is not None and stripped:
            buffer.append(stripped)

    _flush()

    # If the model ignored labels, treat the whole output as the reflection
    if not reflection and raw_text.strip():
        reflection = raw_text.strip()

    return reflection, gm_message, next_quest


# ---------------------------------------------------------------------------
# ORM → schema
# ---------------------------------------------------------------------------


def _to_response(
    record: Reflection, idempotency_key: str | None = None, include_sync: bool = False
) -> ReflectionResponse:
    text, gm_message, next_quest, is_fallback = _unpack(record.text)
    sync = (
        SyncMetadata(
            server_timestamp=datetime.now(UTC),
            resource_version=str(record.id),
            idempotency_key=idempotency_key,
        )
        if include_sync
        else None
    )
    return ReflectionResponse(
        id=str(record.id),
        attempt_id=str(record.attempt_id),
        text=text,
        gm_message=gm_message,
        next_quest_suggestion=next_quest,
        model_name=record.model_name,
        is_fallback=is_fallback,
        created_at=record.created_at,
        sync=sync,
    )


# ---------------------------------------------------------------------------
# Public service methods
# ---------------------------------------------------------------------------


async def create_reflection(
    db: AsyncSession,
    *,
    user_id: UUID,
    attempt_id: UUID,
    text_provider: TextModelProvider | None = None,
    idempotency_key: str | None = None,
) -> ReflectionResponse:
    """Generate and persist a reflection for the given quest attempt.

    Args:
        db:            Active async DB session.
        user_id:       Authenticated player making the request.
        attempt_id:    UUID of the QuestAttempt to reflect on.
        text_provider: TextModelProvider for AI generation.
                       Pass None to force the fallback path (e.g. in tests).

    Returns:
        ReflectionResponse with text, GM message, next-quest suggestion.

    Raises:
        NotFoundException:   Attempt not found.
        ForbiddenException:  Attempt belongs to another user.
        BadRequestException: Attempt must be COMPLETED or ABANDONED (terminal).
    """
    # Load attempt
    result = await db.execute(select(QuestAttempt).where(QuestAttempt.id == attempt_id))
    attempt = result.scalar_one_or_none()
    if attempt is None:
        raise NotFoundException(message="Quest attempt not found")
    if attempt.user_id != user_id:
        raise ForbiddenException(message="You do not own this quest attempt")

    from app.domain.quest_states import TERMINAL_STATUSES, AttemptStatus

    current_status = AttemptStatus(attempt.status)
    if current_status not in TERMINAL_STATUSES:
        raise BadRequestException(
            message=(
                f"Reflections can only be generated for completed or abandoned quests. "
                f"Current status: {current_status.value}"
            ),
            details={"current_status": current_status.value},
        )

    # Load quest for context
    quest_result = await db.execute(select(Quest).where(Quest.id == attempt.quest_id))
    quest = quest_result.scalar_one_or_none()

    # Load player context (completed quest count)
    from app.repositories.quest_repository import QuestAttemptRepository

    stats = await QuestAttemptRepository().get_attempt_stats_by_user_id(db, user_id)

    # Map attempt status to outcome string
    outcome_map = {
        AttemptStatus.COMPLETED: "success",
        AttemptStatus.ABANDONED: "abandoned",
        AttemptStatus.FAILED: "failed",
    }
    outcome = outcome_map.get(current_status, "failed")

    # Build ReflectionRequest
    rr = ReflectionRequest(
        quest_title=quest.title if quest else "Unknown Quest",
        quest_brief=quest.brief if quest else "",
        outcome=outcome,
        earned_xp=attempt.earned_xp,
        personality=quest.personality if quest else "Wizard",
        quest_difficulty=quest.difficulty if quest else "chill",
        player_level=1,  # enriched below
        previous_quest_count=max(0, stats.completed - (1 if outcome == "success" else 0)),
    )

    # Enrich with player level from profile
    from app.repositories.user_repository import PlayerProfileRepository

    profile = await PlayerProfileRepository().get_by_user_id(db, user_id)
    if profile:
        rr.player_level = profile.level

    # Try AI generation
    reflection_text, gm_message, next_quest = "", "", ""
    model_name = FALLBACK_MODEL_NAME
    is_fallback = True

    if text_provider is not None:
        try:
            raw = await text_provider.generate_reflection(rr)
            if raw.text.strip():
                parsed_text, parsed_gm, parsed_next = _parse_model_output(raw.text)
                if parsed_text:
                    reflection_text = parsed_text
                    gm_message = parsed_gm
                    next_quest = parsed_next
                    model_name = raw.model_name
                    is_fallback = False
                    logger.info(
                        "Reflection generated: attempt=%s model=%s outcome=%s",
                        attempt_id,
                        model_name,
                        outcome,
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Reflection AI generation failed (using fallback): %s", exc)

    # Deterministic fallback
    if is_fallback:
        fallback: FallbackReflection = get_fallback(rr)
        reflection_text = fallback.text
        gm_message = fallback.gm_message
        next_quest = fallback.next_quest
        logger.info(
            "Reflection fallback used: attempt=%s personality=%s outcome=%s",
            attempt_id,
            rr.personality,
            outcome,
        )

    # Persist
    packed = _pack(reflection_text, gm_message, next_quest, is_fallback)
    record = Reflection(
        attempt_id=attempt_id,
        text=packed,
        model_name=model_name,
    )
    created = await _reflection_repo.create(db, record)
    return _to_response(created, idempotency_key=idempotency_key, include_sync=True)


async def list_reflections(
    db: AsyncSession,
    *,
    user_id: UUID,
    skip: int = 0,
    limit: int = 20,
) -> ReflectionListResponse:
    """Return all reflections for the authenticated user across all their attempts.

    Args:
        db:      Active async DB session.
        user_id: Authenticated player.
        skip:    Pagination offset.
        limit:   Page size (max 50).
    """
    # Join Reflection → QuestAttempt to filter by user_id
    reflections_q = (
        select(Reflection)
        .join(QuestAttempt, QuestAttempt.id == Reflection.attempt_id)
        .where(QuestAttempt.user_id == user_id)
        .order_by(Reflection.created_at.desc())
        .offset(skip)
        .limit(min(limit, 50))
    )
    count_q = (
        select(func.count(Reflection.id))
        .join(QuestAttempt, QuestAttempt.id == Reflection.attempt_id)
        .where(QuestAttempt.user_id == user_id)
    )

    rows = (await db.execute(reflections_q)).scalars().all()
    total = (await db.execute(count_q)).scalar_one()

    return ReflectionListResponse(
        reflections=[_to_response(r) for r in rows],
        total=total,
    )
