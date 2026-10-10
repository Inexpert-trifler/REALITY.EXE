from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis import AIAnalysis
from app.models.evidence import Evidence
from app.repositories.base import BaseRepository


class EvidenceRepository(BaseRepository[Evidence]):
    """Repository for managing uploaded evidence files."""

    def __init__(self) -> None:
        super().__init__(Evidence)

    async def get_by_attempt_id(self, db: AsyncSession, attempt_id: UUID) -> Sequence[Evidence]:
        """Fetch all evidence submissions for a given quest attempt."""
        result = await db.execute(select(Evidence).where(Evidence.attempt_id == attempt_id))
        return result.scalars().all()


class AIAnalysisRepository(BaseRepository[AIAnalysis]):
    """Repository for vision AI evaluation records."""

    def __init__(self) -> None:
        super().__init__(AIAnalysis)

    async def get_by_evidence_id(self, db: AsyncSession, evidence_id: UUID) -> Sequence[AIAnalysis]:
        """Fetch AI analysis results for an evidence record."""
        result = await db.execute(select(AIAnalysis).where(AIAnalysis.evidence_id == evidence_id))
        return result.scalars().all()
