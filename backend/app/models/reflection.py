import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.quest_attempt import QuestAttempt


class Reflection(Base):
    """Player post-quest reflection and AI dialogue."""

    __tablename__ = "reflections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quest_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    attempt: Mapped["QuestAttempt"] = relationship("QuestAttempt", back_populates="reflections")
