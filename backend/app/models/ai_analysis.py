import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.evidence import Evidence


class AIAnalysis(Base):
    """Result of Vision/Multimodal AI evaluation of uploaded evidence."""

    __tablename__ = "ai_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidences.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    findings_json: Mapped[dict[str, Any] | list[Any]] = mapped_column(JSON, nullable=False)
    completion_recommendation: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    evidence: Mapped["Evidence"] = relationship("Evidence", back_populates="analyses")
