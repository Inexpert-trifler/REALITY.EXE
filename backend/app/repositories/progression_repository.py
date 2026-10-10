from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement
from app.models.xp_transaction import XPTransaction
from app.repositories.base import BaseRepository


class XPTransactionRepository(BaseRepository[XPTransaction]):
    """Repository for auditing XP award/deduction history."""

    def __init__(self) -> None:
        super().__init__(XPTransaction)

    async def get_by_user_id(
        self, db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> Sequence[XPTransaction]:
        """Fetch XP transactions for a user ordered by timestamp."""
        result = await db.execute(
            select(XPTransaction)
            .where(XPTransaction.user_id == user_id)
            .order_by(XPTransaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def reference_id_exists(self, db: AsyncSession, user_id: UUID, reference_id: str) -> bool:
        """Return True if a transaction with this reference_id already exists for the user.

        Used to prevent duplicate XP awards for the same event.
        """
        result = await db.execute(
            select(XPTransaction.id).where(
                XPTransaction.user_id == user_id,
                XPTransaction.reference_id == reference_id,
            )
        )
        return result.scalar_one_or_none() is not None


class AchievementRepository(BaseRepository[Achievement]):
    """Repository for player unlocked achievements."""

    def __init__(self) -> None:
        super().__init__(Achievement)

    async def get_by_user_id(self, db: AsyncSession, user_id: UUID) -> Sequence[Achievement]:
        """Fetch all unlocked achievements for a user."""
        result = await db.execute(
            select(Achievement)
            .where(Achievement.user_id == user_id)
            .order_by(Achievement.unlocked_at.desc())
        )
        return result.scalars().all()

    async def get_by_user_and_key(
        self, db: AsyncSession, user_id: UUID, achievement_key: str
    ) -> Achievement | None:
        """Fetch unlocked achievement by key for a specific user."""
        result = await db.execute(
            select(Achievement).where(
                Achievement.user_id == user_id,
                Achievement.achievement_key == achievement_key,
            )
        )
        return result.scalar_one_or_none()
