"""Quest and QuestAttempt service.

All state-machine transitions live here.  Route handlers must not
contain any transition logic.

Invariants enforced by this service:
  - Every transition is validated through assert_transition().
  - Every attempt operation is scoped to the requesting user's id.
  - A user may only have one non-terminal attempt at a time.
  - Timestamps are set deterministically at transition time.
  - Completing an attempt awards the quest's xp_reward via XPService.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.domain.quest_states import (
    ACTIVE_STATUSES,
    AttemptStatus,
    assert_transition,
)
from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt
from app.repositories.quest_repository import QuestAttemptRepository, QuestRepository
from app.schemas.quest import AttemptResponse, QuestListResponse, QuestResponse
from app.services import xp_service

logger = logging.getLogger(__name__)

_quest_repo = QuestRepository()
_attempt_repo = QuestAttemptRepository()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _quest_to_response(quest: Quest) -> QuestResponse:
    return QuestResponse(
        id=str(quest.id),
        title=quest.title,
        brief=quest.brief,
        duration_minutes=quest.duration_minutes,
        environment=quest.environment,
        difficulty=quest.difficulty,
        play_style=quest.play_style,
        personality=quest.personality,
        objectives=quest.objectives_json
        if isinstance(quest.objectives_json, list)
        else [quest.objectives_json],
        xp_reward=quest.xp_reward,
        evidence_required=quest.evidence_required,
        safety_notes=quest.safety_notes,
        created_at=quest.created_at,
    )


def _attempt_to_response(attempt: QuestAttempt) -> AttemptResponse:
    return AttemptResponse(
        id=str(attempt.id),
        quest_id=str(attempt.quest_id),
        user_id=str(attempt.user_id),
        status=attempt.status,
        started_at=attempt.started_at,
        pocket_started_at=attempt.pocket_started_at,
        completed_at=attempt.completed_at,
        result=attempt.result,
        earned_xp=attempt.earned_xp,
    )


async def _get_attempt_owned_by(
    db: AsyncSession,
    attempt_id: UUID,
    user_id: UUID,
) -> QuestAttempt:
    """Fetch attempt and assert ownership.  Raises 404 or 403 as appropriate."""
    attempt = await _attempt_repo.get_by_id(db, attempt_id)
    if attempt is None:
        raise NotFoundException(message="Quest attempt not found")
    if attempt.user_id != user_id:
        raise ForbiddenException(message="You do not own this quest attempt")
    return attempt


async def _assert_no_active_attempt(db: AsyncSession, user_id: UUID) -> None:
    """Ensure the user has no live attempt before creating a new one."""
    active = await _attempt_repo.get_active_attempt(db, user_id)
    if active is not None:
        raise BadRequestException(
            message="You already have an active quest attempt. "
            "Abandon or complete it before starting a new one.",
            details={"active_attempt_id": str(active.id), "status": active.status},
        )


# ---------------------------------------------------------------------------
# Quest read operations
# ---------------------------------------------------------------------------


async def list_quests(db: AsyncSession, skip: int = 0, limit: int = 20) -> QuestListResponse:
    """Return a paginated list of available quests."""
    quests = await _quest_repo.get_multi(db, skip=skip, limit=limit)
    total_result = await db.execute(select(func.count(Quest.id)))
    total = total_result.scalar_one()
    return QuestListResponse(
        quests=[_quest_to_response(q) for q in quests],
        total=total,
        skip=skip,
        limit=limit,
    )


async def get_quest(db: AsyncSession, quest_id: UUID) -> QuestResponse:
    """Return a single quest by id.  Raises 404 if not found."""
    quest = await _quest_repo.get_by_id(db, quest_id)
    if quest is None:
        raise NotFoundException(message="Quest not found")
    return _quest_to_response(quest)


# ---------------------------------------------------------------------------
# Attempt lifecycle
# ---------------------------------------------------------------------------


async def create_attempt(db: AsyncSession, user_id: UUID, quest_id: UUID) -> AttemptResponse:
    """Create a new CREATED attempt for the given quest.

    Enforces: user has no other live attempt.
    """
    quest = await _quest_repo.get_by_id(db, quest_id)
    if quest is None:
        raise NotFoundException(message="Quest not found")

    await _assert_no_active_attempt(db, user_id)

    attempt = QuestAttempt(
        quest_id=quest_id,
        user_id=user_id,
        status=AttemptStatus.CREATED.value,
        earned_xp=0,
    )
    created = await _attempt_repo.create(db, attempt)
    logger.info("Attempt created: id=%s user=%s quest=%s", created.id, user_id, quest_id)
    return _attempt_to_response(created)


async def start_attempt(db: AsyncSession, user_id: UUID, quest_id: UUID) -> AttemptResponse:
    """Transition CREATED → ACTIVE.

    If no attempt exists yet for this user+quest, it is implicitly created first.
    """
    # Find an existing CREATED attempt for this user+quest combo
    result = await db.execute(
        select(QuestAttempt).where(
            QuestAttempt.user_id == user_id,
            QuestAttempt.quest_id == quest_id,
            QuestAttempt.status == AttemptStatus.CREATED.value,
        )
    )
    attempt = result.scalar_one_or_none()

    if attempt is None:
        # Implicit create — also validates no other live attempt
        await _assert_no_active_attempt(db, user_id)
        quest = await _quest_repo.get_by_id(db, quest_id)
        if quest is None:
            raise NotFoundException(message="Quest not found")
        attempt = QuestAttempt(
            quest_id=quest_id,
            user_id=user_id,
            status=AttemptStatus.CREATED.value,
            earned_xp=0,
        )
        attempt = await _attempt_repo.create(db, attempt)

    current = AttemptStatus(attempt.status)
    assert_transition(current, AttemptStatus.ACTIVE)

    updated = await _attempt_repo.update(db, attempt.id, {"status": AttemptStatus.ACTIVE.value})
    logger.info("Attempt started: id=%s user=%s", attempt.id, user_id)
    return _attempt_to_response(updated)  # type: ignore[arg-type]


async def enter_pocket_mode(db: AsyncSession, user_id: UUID, quest_id: UUID) -> AttemptResponse:
    """Transition ACTIVE → POCKET_MODE."""
    attempt = await _get_active_attempt_for_quest(db, user_id, quest_id)
    assert_transition(AttemptStatus(attempt.status), AttemptStatus.POCKET_MODE)
    updated = await _attempt_repo.update(
        db,
        attempt.id,
        {
            "status": AttemptStatus.POCKET_MODE.value,
            "pocket_started_at": datetime.now(UTC),
        },
    )
    return _attempt_to_response(updated)  # type: ignore[arg-type]


async def return_from_pocket_mode(
    db: AsyncSession, user_id: UUID, quest_id: UUID
) -> AttemptResponse:
    """Transition POCKET_MODE → RETURNED."""
    attempt = await _get_active_attempt_for_quest(db, user_id, quest_id)
    assert_transition(AttemptStatus(attempt.status), AttemptStatus.RETURNED)
    updated = await _attempt_repo.update(db, attempt.id, {"status": AttemptStatus.RETURNED.value})
    return _attempt_to_response(updated)  # type: ignore[arg-type]


async def mark_evidence_pending(db: AsyncSession, user_id: UUID, quest_id: UUID) -> AttemptResponse:
    """Transition RETURNED → EVIDENCE_PENDING."""
    attempt = await _get_active_attempt_for_quest(db, user_id, quest_id)
    assert_transition(AttemptStatus(attempt.status), AttemptStatus.EVIDENCE_PENDING)
    updated = await _attempt_repo.update(
        db, attempt.id, {"status": AttemptStatus.EVIDENCE_PENDING.value}
    )
    return _attempt_to_response(updated)  # type: ignore[arg-type]


async def start_verification(db: AsyncSession, user_id: UUID, quest_id: UUID) -> AttemptResponse:
    """Transition EVIDENCE_PENDING → VERIFYING."""
    attempt = await _get_active_attempt_for_quest(db, user_id, quest_id)
    assert_transition(AttemptStatus(attempt.status), AttemptStatus.VERIFYING)
    updated = await _attempt_repo.update(db, attempt.id, {"status": AttemptStatus.VERIFYING.value})
    return _attempt_to_response(updated)  # type: ignore[arg-type]


async def complete_attempt(db: AsyncSession, user_id: UUID, quest_id: UUID) -> AttemptResponse:
    """Transition VERIFYING (or RETURNED if no evidence required) → COMPLETED.

    Awards the quest's xp_reward to the player.
    """
    attempt = await _get_active_attempt_for_quest(db, user_id, quest_id)
    assert_transition(AttemptStatus(attempt.status), AttemptStatus.COMPLETED)

    quest = await _quest_repo.get_by_id(db, attempt.quest_id)
    xp_to_award = quest.xp_reward if quest else 0

    now = datetime.now(UTC)
    updated = await _attempt_repo.update(
        db,
        attempt.id,
        {
            "status": AttemptStatus.COMPLETED.value,
            "completed_at": now,
            "result": "success",
            "earned_xp": xp_to_award,
        },
    )

    # Award XP — reference_id is the attempt id for idempotency
    if xp_to_award > 0:
        await xp_service.award_xp(
            db,
            user_id,
            xp_to_award,
            reason=f"Quest completed: {quest.title if quest else attempt.quest_id}",
            reference_id=f"quest_complete:{attempt.id}",
        )

    logger.info("Attempt completed: id=%s user=%s xp=%d", attempt.id, user_id, xp_to_award)
    return _attempt_to_response(updated)  # type: ignore[arg-type]


async def pause_attempt(db: AsyncSession, user_id: UUID, quest_id: UUID) -> AttemptResponse:
    """Transition ACTIVE → PAUSED."""
    attempt = await _get_active_attempt_for_quest(db, user_id, quest_id)
    assert_transition(AttemptStatus(attempt.status), AttemptStatus.PAUSED)
    updated = await _attempt_repo.update(db, attempt.id, {"status": AttemptStatus.PAUSED.value})
    return _attempt_to_response(updated)  # type: ignore[arg-type]


async def resume_attempt(db: AsyncSession, user_id: UUID, quest_id: UUID) -> AttemptResponse:
    """Transition PAUSED → ACTIVE."""
    attempt = await _get_active_attempt_for_quest(db, user_id, quest_id)
    assert_transition(AttemptStatus(attempt.status), AttemptStatus.ACTIVE)
    updated = await _attempt_repo.update(db, attempt.id, {"status": AttemptStatus.ACTIVE.value})
    return _attempt_to_response(updated)  # type: ignore[arg-type]


async def abandon_attempt(db: AsyncSession, user_id: UUID, quest_id: UUID) -> AttemptResponse:
    """Transition any live status → ABANDONED."""
    attempt = await _get_active_attempt_for_quest(db, user_id, quest_id)
    assert_transition(AttemptStatus(attempt.status), AttemptStatus.ABANDONED)
    now = datetime.now(UTC)
    updated = await _attempt_repo.update(
        db,
        attempt.id,
        {
            "status": AttemptStatus.ABANDONED.value,
            "completed_at": now,
            "result": "abandoned",
        },
    )
    logger.info("Attempt abandoned: id=%s user=%s", attempt.id, user_id)
    return _attempt_to_response(updated)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Internal helper — find the user's live attempt for a specific quest
# ---------------------------------------------------------------------------


async def _get_active_attempt_for_quest(
    db: AsyncSession, user_id: UUID, quest_id: UUID
) -> QuestAttempt:
    """Return the user's live attempt for quest_id.

    Raises:
        NotFoundException: if no live attempt exists for this user+quest.
        ForbiddenException: if the attempt belongs to another user (shouldn't
                            happen given the WHERE clause, but belt-and-suspenders).
    """
    active_status_values = [s.value for s in ACTIVE_STATUSES]
    result = await db.execute(
        select(QuestAttempt).where(
            QuestAttempt.user_id == user_id,
            QuestAttempt.quest_id == quest_id,
            QuestAttempt.status.in_(active_status_values),
        )
    )
    attempt = result.scalar_one_or_none()
    if attempt is None:
        raise NotFoundException(
            message="No active quest attempt found for this quest. "
            "Start the quest first via POST /quests/{quest_id}/start."
        )
    return attempt
