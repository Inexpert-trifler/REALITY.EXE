"""XP and level progression service.

Rules enforced here:
  - XP amounts must be positive (non-negative, non-zero).
  - Every award creates exactly one XPTransaction.
  - Duplicate awards (same reference_id for the same user) are silently
    skipped and return the unchanged profile — idempotent at the caller.
  - Level is recalculated deterministically from total_xp after every award.
  - The XP curve is read from Settings so it can be overridden without a
    code change.
  - Arbitrary level manipulation via this service is impossible because
    `level` is always derived, never set independently.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestException
from app.models.player_profile import PlayerProfile
from app.models.xp_transaction import XPTransaction
from app.repositories.progression_repository import XPTransactionRepository
from app.repositories.user_repository import PlayerProfileRepository
from app.schemas.player import LevelProgressResponse

logger = logging.getLogger(__name__)

_xp_repo = XPTransactionRepository()
_profile_repo = PlayerProfileRepository()


# ---------------------------------------------------------------------------
# Pure, stateless helpers (easily unit-testable without a DB)
# ---------------------------------------------------------------------------


def calculate_level(total_xp: int, curve: list[int] | None = None) -> int:
    """Return the level that corresponds to *total_xp* using the XP curve.

    The curve is a list where ``curve[i]`` is the XP required to *be at*
    level ``i + 1``.  The player is at the highest level whose threshold
    they have met or exceeded.

    Args:
        total_xp: Non-negative total XP value.
        curve:    Optional override; defaults to ``Settings.XP_CURVE``.

    Returns:
        Level number (1-indexed, minimum 1).
    """
    if curve is None:
        curve = get_settings().XP_CURVE
    if not curve:
        return 1

    level = 1
    for i, threshold in enumerate(curve):
        if total_xp >= threshold:
            level = i + 1
        else:
            break
    return level


def get_progress(total_xp: int, curve: list[int] | None = None) -> LevelProgressResponse:
    """Return detailed level-progress information for *total_xp*.

    Args:
        total_xp: Non-negative total XP.
        curve:    Optional override; defaults to ``Settings.XP_CURVE``.
    """
    if curve is None:
        curve = get_settings().XP_CURVE

    current_level = calculate_level(total_xp, curve)
    level_index = current_level - 1  # 0-based index into curve

    xp_for_current = curve[level_index] if level_index < len(curve) else 0

    # Next-level threshold — None when at max level
    next_index = level_index + 1
    xp_for_next: int | None = curve[next_index] if next_index < len(curve) else None

    xp_into_level = total_xp - xp_for_current

    if xp_for_next is not None:
        band = xp_for_next - xp_for_current
        xp_needed = xp_for_next - total_xp
        progress_pct = round((xp_into_level / band) * 100, 2) if band > 0 else 100.0
    else:
        xp_needed = None
        progress_pct = 100.0

    return LevelProgressResponse(
        current_level=current_level,
        current_xp=total_xp,
        xp_for_current_level=xp_for_current,
        xp_for_next_level=xp_for_next,
        xp_into_level=xp_into_level,
        xp_needed_for_next=xp_needed,
        progress_percent=progress_pct,
    )


# ---------------------------------------------------------------------------
# Stateful service methods (require DB session)
# ---------------------------------------------------------------------------


async def award_xp(
    db: AsyncSession,
    user_id: UUID,
    amount: int,
    reason: str,
    reference_id: str | None = None,
) -> PlayerProfile:
    """Award *amount* XP to a user, recording an XPTransaction.

    Args:
        db:           Active async DB session.
        user_id:      Target player's UUID.
        amount:       Positive integer XP to award.
        reason:       Human-readable description (stored in XPTransaction).
        reference_id: Optional idempotency key.  If provided and a
                      transaction with this key already exists for this
                      user, the award is skipped and the current profile
                      is returned unchanged.

    Returns:
        Updated PlayerProfile with recalculated level.

    Raises:
        BadRequestException: if *amount* is ≤ 0.
        BadRequestException: if no profile exists for *user_id*.
    """
    if amount <= 0:
        raise BadRequestException(
            message="XP amount must be positive",
            details={"amount": amount},
        )

    # Idempotency: skip if this exact event was already processed
    if reference_id is not None:
        already_processed = await _xp_repo.reference_id_exists(db, user_id, reference_id)
        if already_processed:
            logger.info("Duplicate XP award skipped: user=%s ref=%s", user_id, reference_id)
            profile = await _profile_repo.get_by_user_id(db, user_id)
            if profile is None:
                raise BadRequestException(message="Player profile not found")
            return profile

    profile = await _profile_repo.get_by_user_id(db, user_id)
    if profile is None:
        raise BadRequestException(message="Player profile not found")

    # Record the transaction first (audit log)
    tx = XPTransaction(
        user_id=user_id,
        amount=amount,
        reason=reason,
        reference_id=reference_id,
    )
    await _xp_repo.create(db, tx)

    # Update profile — level is always derived, never set independently
    new_total = profile.total_xp + amount
    new_level = calculate_level(new_total)

    updated = await _profile_repo.update(
        db,
        profile.id,
        {"total_xp": new_total, "level": new_level},
    )
    if updated is None:
        raise BadRequestException(message="Failed to update player profile")

    logger.info(
        "XP awarded",
        extra={
            "event": "xp_transaction",
            "user_id": str(user_id),
            "amount": amount,
            "reason": reason,
            "new_total_xp": new_total,
            "new_level": new_level,
        },
    )
    return updated
