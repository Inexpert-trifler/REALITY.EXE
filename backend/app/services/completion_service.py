"""CompletionService — orchestrates the full quest completion pipeline.

Pipeline on success:
  1. Validate attempt ownership and state (must be VERIFYING).
  2. Check for idempotency — if already COMPLETED, return cached result.
  3. Transition attempt → COMPLETED (via quest_service.complete_attempt).
     complete_attempt already awards XP with reference_id=f'quest_complete:{attempt_id}'
     so XP is inherently idempotent via XPTransaction.reference_id.
  4. Detect level-up (compare level before/after).
  5. Evaluate achievements (stubbed — framework ready for full impl).
  6. Generate reflection via text provider.
  7. Return CompletionResponse with all side-effects.

For non-success outcomes (INCOMPLETE / UNCERTAIN / UNSAFE):
  - Attempt is NOT completed.
  - XP is NOT awarded.
  - Player is given appropriate guidance.

Idempotency guarantee:
  - XP reference_id = 'quest_complete:{attempt_id}'
  - Calling complete() twice returns the same result; XP is only credited once.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import ReflectionRequest, TextModelProvider
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.domain.quest_states import AttemptStatus
from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt
from app.models.reflection import Reflection
from app.repositories.reflection_repository import ReflectionRepository
from app.repositories.user_repository import PlayerProfileRepository
from app.schemas.completion import (
    CompletionResponse,
    LevelUpInfo,
    NewAchievement,
)
from app.services import quest_service

logger = logging.getLogger(__name__)

_profile_repo = PlayerProfileRepository()
_reflection_repo = ReflectionRepository()


async def _evaluate_achievements(
    db: AsyncSession,
    user_id: UUID,
    quest: Quest | None,
) -> list[NewAchievement]:
    """Delegate achievement evaluation to AchievementService.

    Returns list of newly unlocked achievements as NewAchievement schema items.
    """
    from app.services.achievement_service import evaluate_user

    newly = await evaluate_user(db, user_id=user_id, quest=quest)
    return [NewAchievement(key=a.key, unlocked_at=a.unlocked_at) for a in newly]


async def _generate_reflection(
    db: AsyncSession,
    attempt: QuestAttempt,
    quest: Quest | None,
    earned_xp: int,
    text_provider: TextModelProvider | None,
) -> str | None:
    """Generate a reflection via the text provider and persist it.

    Returns the reflection text, or None if generation fails/unavailable.
    """
    if text_provider is None or quest is None:
        return None

    try:
        raw = await text_provider.generate_reflection(
            ReflectionRequest(
                quest_title=quest.title,
                quest_brief=quest.brief,
                outcome="success",
                earned_xp=earned_xp,
                personality=quest.personality,
            )
        )
        text = raw.text.strip()
        if not text:
            return None

        reflection = Reflection(
            attempt_id=attempt.id,
            text=text,
            model_name=raw.model_name,
        )
        await _reflection_repo.create(db, reflection)
        return text

    except Exception as exc:  # noqa: BLE001
        logger.warning("Reflection generation failed (non-fatal): %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public service function
# ---------------------------------------------------------------------------


async def complete_quest(
    db: AsyncSession,
    *,
    user_id: UUID,
    quest_id: UUID,
    text_provider: TextModelProvider | None = None,
) -> CompletionResponse:
    """Execute the full quest completion pipeline.

    The attempt must be in VERIFYING state for a full completion.
    Calling this method twice is safe — the second call detects the
    already-COMPLETED attempt and returns the cached result (idempotent).

    Args:
        db:            Active async DB session.
        user_id:       Authenticated player.
        quest_id:      Quest being completed.
        text_provider: Optional text provider for reflection generation.
                       Pass None to skip reflection (e.g. in tests).

    Returns:
        CompletionResponse with XP, level-up, achievements, and reflection.
    """
    # Fetch the most recent attempt for this user+quest
    result = await db.execute(
        select(QuestAttempt)
        .where(
            QuestAttempt.user_id == user_id,
            QuestAttempt.quest_id == quest_id,
        )
        .order_by(QuestAttempt.started_at.desc())
    )
    attempt = result.scalars().first()
    if attempt is None:
        raise NotFoundException(message="No quest attempt found for this quest")
    if attempt.user_id != user_id:
        raise ForbiddenException(message="You do not own this quest attempt")

    current_status = AttemptStatus(attempt.status)

    # Idempotency: already completed → return cached result
    if current_status == AttemptStatus.COMPLETED:
        logger.info("Idempotent completion: attempt=%s already COMPLETED", attempt.id)
        profile = await _profile_repo.get_by_user_id(db, user_id)
        quest_r = await db.execute(select(Quest).where(Quest.id == quest_id))
        quest = quest_r.scalar_one_or_none()
        return CompletionResponse(
            attempt_id=str(attempt.id),
            quest_id=str(quest_id),
            status="COMPLETED",
            earned_xp=attempt.earned_xp,
            total_xp=profile.total_xp if profile else 0,
            level=profile.level if profile else 1,
            level_up=LevelUpInfo(
                leveled_up=False,
                old_level=profile.level if profile else 1,
                new_level=profile.level if profile else 1,
            ),
            new_achievements=[],
            reflection=None,
            idempotent=True,
        )

    # Must be in VERIFYING to proceed
    if current_status != AttemptStatus.VERIFYING:
        raise BadRequestException(
            message=(
                f"Quest cannot be completed from '{current_status}' state. "
                "The attempt must be in VERIFYING state."
            ),
            details={"current_status": current_status.value, "required_status": "VERIFYING"},
        )

    # Load quest for XP and context
    quest_r = await db.execute(select(Quest).where(Quest.id == quest_id))
    quest = quest_r.scalar_one_or_none()

    # Record level before completion
    profile_before = await _profile_repo.get_by_user_id(db, user_id)
    level_before = profile_before.level if profile_before else 1

    # Transition VERIFYING → COMPLETED + award XP (via existing quest_service)
    # complete_attempt uses reference_id=f'quest_complete:{attempt.id}' for idempotency
    attempt_response = await quest_service.complete_attempt(db, user_id, quest_id)

    # Fetch updated profile after XP award
    profile_after = await _profile_repo.get_by_user_id(db, user_id)
    level_after = profile_after.level if profile_after else 1
    total_xp = profile_after.total_xp if profile_after else 0

    # Detect level-up
    leveled_up = level_after > level_before

    logger.info(
        "Quest completed: attempt=%s user=%s xp=%d level=%d->%d",
        attempt.id,
        user_id,
        attempt_response.earned_xp,
        level_before,
        level_after,
    )

    # Evaluate achievements
    new_achievements = await _evaluate_achievements(db, user_id, quest)

    # Generate reflection
    reflection_text = await _generate_reflection(
        db, attempt, quest, attempt_response.earned_xp, text_provider
    )

    return CompletionResponse(
        attempt_id=str(attempt.id),
        quest_id=str(quest_id),
        status="COMPLETED",
        earned_xp=attempt_response.earned_xp,
        total_xp=total_xp,
        level=level_after,
        level_up=LevelUpInfo(
            leveled_up=leveled_up,
            old_level=level_before,
            new_level=level_after,
        ),
        new_achievements=new_achievements,
        reflection=reflection_text,
        idempotent=False,
    )
