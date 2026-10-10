from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.player_profile import PlayerProfile
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User persistence and lookup operations."""

    def __init__(self) -> None:
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """Fetch user by email address."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        """Fetch user by username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_id_with_profile(self, db: AsyncSession, user_id: UUID) -> User | None:
        """Fetch user by primary key, eagerly loading the player profile.

        Use this instead of ``get_by_id`` whenever the caller needs
        ``user.profile`` to avoid lazy-load errors in async contexts.
        """
        result = await db.execute(
            select(User).where(User.id == user_id).options(selectinload(User.profile))
        )
        return result.scalar_one_or_none()


class PlayerProfileRepository(BaseRepository[PlayerProfile]):
    """Repository for PlayerProfile gamification data."""

    def __init__(self) -> None:
        super().__init__(PlayerProfile)

    async def get_by_user_id(self, db: AsyncSession, user_id: UUID) -> PlayerProfile | None:
        """Fetch player profile by associated user ID."""
        result = await db.execute(select(PlayerProfile).where(PlayerProfile.user_id == user_id))
        return result.scalar_one_or_none()
