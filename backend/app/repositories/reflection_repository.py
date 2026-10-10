from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reflection import Reflection
from app.repositories.base import BaseRepository


class ReflectionRepository(BaseRepository[Reflection]):
    """Repository for player reflections and AI dialogue."""

    def __init__(self) -> None:
        super().__init__(Reflection)

    async def get_by_attempt_id(self, db: AsyncSession, attempt_id: UUID) -> Sequence[Reflection]:
        """Fetch all reflections for a given attempt."""
        result = await db.execute(
            select(Reflection)
            .where(Reflection.attempt_id == attempt_id)
            .order_by(Reflection.created_at.asc())
        )
        return result.scalars().all()
