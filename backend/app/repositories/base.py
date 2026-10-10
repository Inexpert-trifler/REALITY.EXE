from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async repository providing standard CRUD database operations."""

    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get_by_id(self, db: AsyncSession, id: UUID) -> ModelType | None:
        """Fetch a single record by primary key UUID."""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> Sequence[ModelType]:
        """Fetch multiple records with offset pagination."""
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in: ModelType) -> ModelType:
        """Persist a new entity into the database."""
        db.add(obj_in)
        await db.flush()
        await db.refresh(obj_in)
        return obj_in

    async def update(self, db: AsyncSession, id: UUID, values: dict[str, Any]) -> ModelType | None:
        """Update an existing record by UUID."""
        await db.execute(update(self.model).where(self.model.id == id).values(**values))
        await db.flush()
        return await self.get_by_id(db, id)

    async def delete(self, db: AsyncSession, id: UUID) -> bool:
        """Delete a record by UUID."""
        result = await db.execute(delete(self.model).where(self.model.id == id))
        await db.flush()
        return result.rowcount > 0
