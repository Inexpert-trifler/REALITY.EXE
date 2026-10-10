import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.achievement import Achievement
    from app.models.player_profile import PlayerProfile
    from app.models.quest_attempt import QuestAttempt
    from app.models.xp_transaction import XPTransaction


class User(Base):
    """User account entity."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    profile: Mapped[Optional["PlayerProfile"]] = relationship(
        "PlayerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    attempts: Mapped[list["QuestAttempt"]] = relationship(
        "QuestAttempt", back_populates="user", cascade="all, delete-orphan"
    )
    xp_transactions: Mapped[list["XPTransaction"]] = relationship(
        "XPTransaction", back_populates="user", cascade="all, delete-orphan"
    )
    achievements: Mapped[list["Achievement"]] = relationship(
        "Achievement", back_populates="user", cascade="all, delete-orphan"
    )
