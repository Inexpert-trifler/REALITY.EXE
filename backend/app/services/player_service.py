"""Player profile service.

Handles reading and updating profile fields.
XP and level are intentionally NOT modifiable here — use xp_service.award_xp.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.player_profile import PlayerProfile
from app.repositories.progression_repository import AchievementRepository
from app.repositories.quest_repository import QuestAttemptRepository
from app.repositories.user_repository import PlayerProfileRepository
from app.schemas.player import (
    PlayerStatsResponse,
    ProfilePatchRequest,
    ProfileResponse,
)

logger = logging.getLogger(__name__)

_profile_repo = PlayerProfileRepository()
_attempt_repo = QuestAttemptRepository()
_achievement_repo = AchievementRepository()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_response(profile: PlayerProfile) -> ProfileResponse:
    return ProfileResponse(
        id=str(profile.id),
        user_id=str(profile.user_id),
        display_name=profile.display_name,
        level=profile.level,
        total_xp=profile.total_xp,
        preferred_personality=profile.preferred_personality,
        preferred_play_style=profile.preferred_play_style,
    )


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


async def get_profile(db: AsyncSession, requesting_user_id: UUID) -> ProfileResponse:
    """Return the profile for the authenticated player.

    Args:
        db:                   Active async DB session.
        requesting_user_id:   UUID of the currently authenticated user.

    Raises:
        NotFoundException: if no profile exists (should not happen after
                           registration, but defensive).
    """
    profile = await _profile_repo.get_by_user_id(db, requesting_user_id)
    if profile is None:
        raise NotFoundException(message="Player profile not found")
    return _to_response(profile)


async def patch_profile(
    db: AsyncSession,
    requesting_user_id: UUID,
    payload: ProfilePatchRequest,
) -> ProfileResponse:
    """Update allowed profile fields for the authenticated player.

    Only fields explicitly set in *payload* are written.
    XP, level, and user_id are never touched here.

    Raises:
        NotFoundException:  if no profile exists.
        ForbiddenException: if the profile does not belong to the caller
                            (extra guard, should be unreachable given the
                            dependency chain, but belt-and-suspenders).
    """
    profile = await _profile_repo.get_by_user_id(db, requesting_user_id)
    if profile is None:
        raise NotFoundException(message="Player profile not found")

    if profile.user_id != requesting_user_id:
        raise ForbiddenException(message="You cannot modify another player's profile")

    # Build update dict from only the fields the caller provided
    updates: dict[str, object] = {}
    if payload.display_name is not None:
        updates["display_name"] = payload.display_name
    if payload.preferred_personality is not None:
        updates["preferred_personality"] = payload.preferred_personality
    if payload.preferred_play_style is not None:
        updates["preferred_play_style"] = payload.preferred_play_style

    if not updates:
        # Nothing to change — return current state
        return _to_response(profile)

    updated = await _profile_repo.update(db, profile.id, updates)
    if updated is None:
        raise NotFoundException(message="Player profile not found after update")

    logger.info("Profile updated: user=%s fields=%s", requesting_user_id, list(updates.keys()))
    return _to_response(updated)


async def get_stats(db: AsyncSession, requesting_user_id: UUID) -> PlayerStatsResponse:
    """Return aggregated gameplay statistics for the authenticated player.

    Delegates to history_service.get_extended_stats for the full picture,
    then returns the PlayerStatsResponse for backward compatibility.

    Raises:
        NotFoundException: if no profile exists.
    """
    from app.services.history_service import get_extended_stats

    extended = await get_extended_stats(db, user_id=requesting_user_id)

    return PlayerStatsResponse(
        user_id=str(requesting_user_id),
        level=extended.level,
        total_xp=extended.total_xp,
        total_quests=extended.total_quests,
        completed_quests=extended.completed_quests,
        abandoned_quests=extended.abandoned_quests,
        completion_rate=extended.completion_rate,
        achievements_count=extended.achievements_count,
        favorite_play_style=extended.favorite_play_style,
        avg_quest_duration_minutes=extended.avg_quest_duration_minutes,
        level_progress=extended.level_progress,
    )
