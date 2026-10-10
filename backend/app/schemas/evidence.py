"""Evidence upload schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.sync import SyncMetadata


class EvidenceUploadResponse(BaseModel):
    """Returned by POST /api/v1/evidence/upload on success."""

    evidence_id: str
    attempt_id: str
    status: str = "uploaded"
    mime_type: str
    size_bytes: int
    checksum: str  # SHA-256 hex digest (safe to expose — not a secret)
    created_at: datetime
    sync: SyncMetadata  # offline-first metadata

    model_config = {"from_attributes": True}
