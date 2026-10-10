import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.quest import Quest
    from app.models.reflection import Reflection
    from app.models.user import User


class QuestAttempt(Base):
    """Player quest attempt tracking lifecycle and status."""

    __tablename__ = "quest_attempts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    quest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="ACTIVE", nullable=False, index=True
    )  # CREATED, ACTIVE, POCKET_MODE, RETURNED, EVIDENCE_PENDING, VERIFYING, COMPLETED, ABANDONED
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    pocket_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[str | None] = mapped_column(String(50), nullable=True)
    earned_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="attempts")
    quest: Mapped["Quest"] = relationship("Quest", back_populates="attempts")
    evidences: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="attempt", cascade="all, delete-orphan"
    )
    reflections: Mapped[list["Reflection"]] = relationship(
        "Reflection", back_populates="attempt", cascade="all, delete-orphan"
    )
