"""Evidence upload route handlers."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, get_storage_provider
from app.db.session import get_db
from app.schemas.errors import AUTH_RESPONSES, Error400, Error403, Error404, Error422
from app.schemas.evidence import EvidenceUploadResponse
from app.services import evidence_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evidence", tags=["Evidence"])

_HARD_READ_LIMIT = 11 * 1024 * 1024  # 11 MB


@router.post(
    "/upload",
    response_model=EvidenceUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload evidence for a quest attempt",
    responses={
        201: {"description": "Evidence uploaded and metadata persisted"},
        400: {
            "model": Error400,
            "description": (
                "File too large · Invalid MIME type · Extension mismatch · "
                "Failed image decode · Attempt in wrong state"
            ),
        },
        403: {"model": Error403, "description": "Attempt belongs to another player"},
        404: {"model": Error404, "description": "Quest attempt not found"},
        422: {"model": Error422, "description": "Missing required form fields"},
        **AUTH_RESPONSES,
    },
)
async def upload_evidence(
    current_user: CurrentUser,
    attempt_id: UUID = Form(
        ...,
        description="UUID of the QuestAttempt this evidence belongs to",
    ),
    file: UploadFile = File(
        ...,
        description="Image file — JPEG, PNG, or WEBP, maximum 10 MB",
    ),
    db: AsyncSession = Depends(get_db),
    storage=Depends(get_storage_provider),
    x_idempotency_key: str | None = Header(
        default=None,
        alias="X-Idempotency-Key",
        description="Optional client-supplied idempotency key for offline-first sync",
    ),
) -> EvidenceUploadResponse:
    """Upload an image as evidence for quest completion verification.

    **Accepted formats**: JPEG (`.jpg`, `.jpeg`), PNG (`.png`), WEBP (`.webp`)

    **Maximum size**: 10 MB

    The file undergoes multiple security checks:
    1. Size limit enforced before any I/O
    2. MIME type validated against an allowlist (client `Content-Type` is not trusted)
    3. File extension cross-checked against the declared MIME type
    4. Pillow decode validation — confirms the file is a real image, not a renamed executable

    The attempt must be in `RETURNED` or `EVIDENCE_PENDING` state.

    The response includes `sync` metadata (`server_timestamp`, `resource_version`,
    `idempotency_key`) for offline-first clients.

    **Requires**: `Authorization: Bearer <token>`
    """
    file_data = await file.read(_HARD_READ_LIMIT)
    return await evidence_service.upload_evidence(
        db,
        user_id=current_user.id,
        attempt_id=attempt_id,
        file_data=file_data,
        filename=file.filename or "",
        content_type=file.content_type or "",
        storage=storage,
        idempotency_key=x_idempotency_key,
    )
