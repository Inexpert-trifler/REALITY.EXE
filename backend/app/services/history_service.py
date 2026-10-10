"""HistoryService — paginated, filtered, sorted quest attempt history.

All queries are scoped to the authenticated user — cross-user access is
impossible by design because user_id is always passed from the auth dependency,
never from a user-controllable request field.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.ai_analysis import AIAnalysis
from app.models.evidence import Evidence
from app.models.quest_attempt import QuestAttempt
from app.repositories.progression_repository import AchievementRepository
from app.repositories.quest_repository import QuestAttemptRepository
from app.repositories.user_repository import PlayerProfileRepository
from app.schemas.history import (
    AttemptHistoryItem,
    EvidenceStatusSummary,
    ExtendedPlayerStatsResponse,
    QuestHistoryResponse,
)
from app.services.xp_service import get_progress

logger = logging.getLogger(__name__)

_attempt_repo = QuestAttemptRepository()
_profile_repo = PlayerProfileRepository()
_achievement_repo = AchievementRepository()


# ---------------------------------------------------------------------------
# Helper — evidence summary for one attempt
# ---------------------------------------------------------------------------


async def _get_evidence_summary(db: AsyncSession, attempt_id: UUID) -> EvidenceStatusSummary:
    """Return evidence count and latest AI analysis outcome for one attempt."""
    evidences_result = await db.execute(select(Evidence).where(Evidence.attempt_id == attempt_id))
    evidences = evidences_result.scalars().all()
    count = len(evidences)
    if count == 0:
        return EvidenceStatusSummary(
            evidence_count=0, latest_ai_outcome=None, latest_confidence=None
        )

    # Get most recent analysis across all evidence for this attempt
    evidence_ids = [e.id for e in evidences]
    analysis_result = await db.execute(
        select(AIAnalysis)
        .where(AIAnalysis.evidence_id.in_(evidence_ids))
        .order_by(AIAnalysis.created_at.desc())
        .limit(1)
    )
    analysis = analysis_result.scalar_one_or_none()
    return EvidenceStatusSummary(
        evidence_count=count,
        latest_ai_outcome=analysis.completion_recommendation if analysis else None,
        latest_confidence=analysis.confidence if analysis else None,
    )


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


async def get_history(
    db: AsyncSession,
    *,
    user_id: UUID,
    skip: int = 0,
    limit: int = 20,
    status_filter: str | None = None,
    sort_by: str = "started_at",
    sort_dir: str = "desc",
) -> QuestHistoryResponse:
    """Return paginated quest attempt history for the authenticated player.

    Args:
        db:            Active async DB session.
        user_id:       Authenticated player.
        skip:          Pagination offset.
        limit:         Page size (max 50).
        status_filter: Optional status string (case-insensitive).
        sort_by:       "started_at" | "completed_at" | "earned_xp"
        sort_dir:      "asc" | "desc"
    """
    limit = min(limit, 50)
    attempts, total = await _attempt_repo.get_by_user_id_with_quest(
        db,
        user_id=user_id,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    items: list[AttemptHistoryItem] = []
    for attempt in attempts:
        quest = attempt.quest  # eagerly loaded
        evidence_summary = await _get_evidence_summary(db, attempt.id)
        items.append(
            AttemptHistoryItem(
                attempt_id=str(attempt.id),
                quest_id=str(attempt.quest_id),
                quest_title=quest.title if quest else "Unknown Quest",
                quest_difficulty=quest.difficulty if quest else "",
                quest_play_style=quest.play_style if quest else "",
                quest_duration_minutes=quest.duration_minutes if quest else 0,
                status=attempt.status,
                earned_xp=attempt.earned_xp,
                started_at=attempt.started_at,
                completed_at=attempt.completed_at,
                used_pocket_mode=attempt.pocket_started_at is not None,
                evidence=evidence_summary,
            )
        )

    return QuestHistoryResponse(attempts=items, total=total, skip=skip, limit=limit)


async def get_attempt_detail(
    db: AsyncSession,
    *,
    user_id: UUID,
    attempt_id: UUID,
) -> AttemptHistoryItem:
    """Return detail for a single attempt, verifying ownership.

    Raises:
        NotFoundException:   Attempt not found.
        ForbiddenException:  Attempt belongs to another user.
    """
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(QuestAttempt)
        .where(QuestAttempt.id == attempt_id)
        .options(selectinload(QuestAttempt.quest))
    )
    attempt = result.scalar_one_or_none()
    if attempt is None:
        raise NotFoundException(message="Quest attempt not found")
    if attempt.user_id != user_id:
        raise ForbiddenException(message="You do not own this quest attempt")

    quest = attempt.quest
    evidence_summary = await _get_evidence_summary(db, attempt.id)
    return AttemptHistoryItem(
        attempt_id=str(attempt.id),
        quest_id=str(attempt.quest_id),
        quest_title=quest.title if quest else "Unknown Quest",
        quest_difficulty=quest.difficulty if quest else "",
        quest_play_style=quest.play_style if quest else "",
        quest_duration_minutes=quest.duration_minutes if quest else 0,
        status=attempt.status,
        earned_xp=attempt.earned_xp,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        used_pocket_mode=attempt.pocket_started_at is not None,
        evidence=evidence_summary,
    )


# ---------------------------------------------------------------------------
# Extended stats (GET /player/stats enhancement)
# ---------------------------------------------------------------------------


async def get_extended_stats(
    db: AsyncSession,
    *,
    user_id: UUID,
) -> ExtendedPlayerStatsResponse:
    """Return enriched player stats including play-style and duration data."""
    profile = await _profile_repo.get_by_user_id(db, user_id)
    if profile is None:
        from app.core.exceptions import NotFoundException

        raise NotFoundException(message="Player profile not found")

    extended = await _attempt_repo.get_extended_stats_by_user_id(db, user_id)
    achievements = await _achievement_repo.get_by_user_id(db, user_id)
    completion_rate = round(extended.completed / extended.total, 4) if extended.total > 0 else 0.0
    level_progress = get_progress(profile.total_xp)

    return ExtendedPlayerStatsResponse(
        user_id=str(user_id),
        level=profile.level,
        total_xp=profile.total_xp,
        total_quests=extended.total,
        completed_quests=extended.completed,
        abandoned_quests=extended.abandoned,
        completion_rate=completion_rate,
        achievements_count=len(achievements),
        favorite_play_style=extended.favorite_play_style,
        avg_quest_duration_minutes=extended.avg_duration_minutes,
        level_progress=level_progress,
    )
