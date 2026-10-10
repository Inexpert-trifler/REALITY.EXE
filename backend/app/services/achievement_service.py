"""AchievementService — evaluate, unlock, and query player achievements.

Every unlock is idempotent:
  - Code-level guard: `get_by_user_and_key → if None: create`
  - DB-level guard:   `UniqueConstraint(user_id, achievement_key)` on the table

Evaluation for each achievement:
  first_contact  – 1st ever COMPLETED attempt
  touch_grass    – ≥3 COMPLETED attempts on outdoor environments
  curious_mind   – ≥5 COMPLETED attempts with play_style == "observer"
  chaos_agent    – COMPLETED attempt with difficulty == "chaos"
  pocket_player  – ≥5 COMPLETED attempts where pocket_started_at IS NOT NULL
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.achievements.definitions import ACHIEVEMENTS, get_definition
from app.models.achievement import Achievement
from app.models.quest import Quest
from app.repositories.progression_repository import AchievementRepository
from app.repositories.quest_repository import QuestAttemptRepository
from app.schemas.achievement import AchievementListResponse, AchievementResponse

logger = logging.getLogger(__name__)

_ach_repo = AchievementRepository()
_attempt_repo = QuestAttemptRepository()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_response(record: Achievement) -> AchievementResponse:
    defn = get_definition(record.achievement_key)
    return AchievementResponse(
        id=str(record.id),
        key=record.achievement_key,
        name=defn.name if defn else record.achievement_key,
        description=defn.description if defn else "",
        icon=defn.icon if defn else "🏆",
        unlocked_at=record.unlocked_at,
    )


async def _unlock_if_new(
    db: AsyncSession,
    user_id: UUID,
    key: str,
    newly_unlocked: list[AchievementResponse],
) -> None:
    """Unlock *key* for *user_id* if not already held.  Idempotent."""
    existing = await _ach_repo.get_by_user_and_key(db, user_id, key)
    if existing is not None:
        return
    record = Achievement(user_id=user_id, achievement_key=key)
    created = await _ach_repo.create(db, record)
    newly_unlocked.append(_to_response(created))
    logger.info("Achievement unlocked: user=%s key=%s", user_id, key)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def evaluate_user(
    db: AsyncSession,
    user_id: UUID,
    quest: Quest | None = None,
) -> list[AchievementResponse]:
    """Evaluate all achievement conditions for *user_id* and unlock any new ones.

    Called after every successful quest completion.  Safe to call multiple
    times — already-held achievements are skipped.

    Args:
        db:    Active async DB session.
        user_id: The player to evaluate.
        quest: The just-completed Quest (used for per-quest conditions).

    Returns:
        List of achievements newly unlocked in this call.
    """
    newly_unlocked: list[AchievementResponse] = []

    # --- first_contact: first ever completion --------------------------------
    completed_total = (await _attempt_repo.get_attempt_stats_by_user_id(db, user_id)).completed
    if completed_total >= 1:
        await _unlock_if_new(db, user_id, "first_contact", newly_unlocked)

    # --- chaos_agent: completing a chaos difficulty quest --------------------
    if quest is not None and quest.difficulty == "chaos":
        await _unlock_if_new(db, user_id, "chaos_agent", newly_unlocked)

    # --- touch_grass: ≥3 completed outdoor quests ---------------------------
    outdoor_count = await _attempt_repo.count_completed_outdoor(db, user_id)
    if outdoor_count >= ACHIEVEMENTS["touch_grass"].threshold:
        await _unlock_if_new(db, user_id, "touch_grass", newly_unlocked)

    # --- curious_mind: ≥5 completed observer quests -------------------------
    observer_count = await _attempt_repo.count_completed_by_play_style(db, user_id, "observer")
    if observer_count >= ACHIEVEMENTS["curious_mind"].threshold:
        await _unlock_if_new(db, user_id, "curious_mind", newly_unlocked)

    # --- pocket_player: ≥5 completed quests using pocket mode ---------------
    pocket_count = await _attempt_repo.count_completed_with_pocket_mode(db, user_id)
    if pocket_count >= ACHIEVEMENTS["pocket_player"].threshold:
        await _unlock_if_new(db, user_id, "pocket_player", newly_unlocked)

    return newly_unlocked


async def unlock(
    db: AsyncSession,
    user_id: UUID,
    key: str,
) -> AchievementResponse | None:
    """Manually unlock a single achievement. Idempotent — returns None if already held.

    Use this for special/one-off unlocks outside the normal evaluation flow.
    """
    if key not in ACHIEVEMENTS:
        logger.warning("Attempted to unlock unknown achievement key: %s", key)
        return None
    newly: list[AchievementResponse] = []
    await _unlock_if_new(db, user_id, key, newly)
    return newly[0] if newly else None


async def get_user_achievements(
    db: AsyncSession,
    user_id: UUID,
) -> AchievementListResponse:
    """Return all unlocked achievements for *user_id* with full metadata.

    Augments each DB record with the static definition metadata (name,
    description, icon).  Achievements not in the registry are still returned
    but with placeholder metadata.
    """
    records = await _ach_repo.get_by_user_id(db, user_id)
    unlocked = [_to_response(r) for r in records]

    # Build the full catalogue with unlocked_at filled in where applicable
    unlocked_map = {r.key: r for r in unlocked}
    all_defs = [
        AchievementResponse(
            id=unlocked_map[key].id if key in unlocked_map else "",
            key=key,
            name=defn.name,
            description=defn.description,
            icon=defn.icon,
            unlocked_at=unlocked_map[key].unlocked_at if key in unlocked_map else None,
        )
        for key, defn in ACHIEVEMENTS.items()
    ]

    return AchievementListResponse(
        unlocked_count=len(unlocked),
        achievements=all_defs,
    )
