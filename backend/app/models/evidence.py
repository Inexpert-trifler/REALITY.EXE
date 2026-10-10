import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ai_analysis import AIAnalysis
    from app.models.quest_attempt import QuestAttempt


class Evidence(Base):
    """Uploaded evidence file for quest completion verification."""

    __tablename__ = "evidences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quest_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(550), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    attempt: Mapped["QuestAttempt"] = relationship("QuestAttempt", back_populates="evidences")
    analyses: Mapped[list["AIAnalysis"]] = relationship(
        "AIAnalysis", back_populates="evidence", cascade="all, delete-orphan"
    )
