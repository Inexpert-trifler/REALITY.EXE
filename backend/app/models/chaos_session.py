"""ChaosSession — tracks a chain of connected Chaos quests.

One ChaosSession ties together multiple quest attempts in a continuation
chain.  The depth counter prevents unbounded chains.  A player can exit
the chain at any time; the session is then closed.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.quest_attempt import QuestAttempt
    from app.models.user import User


class ChaosSession(Base):
    """A Chaos Mode quest chain session."""

    __tablename__ = "chaos_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    root_attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quest_attempts.id", ondelete="CASCADE"), nullable=False
    )
    current_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("quest_attempts.id", ondelete="SET NULL"), nullable=True
    )
    # Chain metadata
    chain_depth: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_chain_depth: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="ACTIVE", nullable=False, index=True
    )  # ACTIVE | COMPLETED | EXITED
    discovery_context: Mapped[str | None] = mapped_column(String(2000), nullable=True)
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

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    root_attempt: Mapped["QuestAttempt"] = relationship(
        "QuestAttempt", foreign_keys=[root_attempt_id]
    )
    current_attempt: Mapped["QuestAttempt | None"] = relationship(
        "QuestAttempt", foreign_keys=[current_attempt_id]
    )
