"""Evidence upload service.

Enforces all security rules before touching storage or the database:
  1. Attempt ownership — the upload must belong to the authenticated user.
  2. Attempt state  — only RETURNED or EVIDENCE_PENDING allow new uploads.
  3. File size      — reject before reading the full body.
  4. MIME type      — validated against an allowlist (not the browser Content-Type).
  5. Extension      — cross-checked against the MIME type.
  6. Image decode   — PIL decode validates the file is a real image, not a
                      disguised executable with a renamed extension.
  7. Checksum       — SHA-256 of the raw bytes stored for integrity audits.
  8. Storage key    — random UUID-based path; never derived from user input.
  9. DB persistence — Evidence record created only after successful storage write.

Never log file contents, checksums as secrets, or user-provided filenames.
"""

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.domain.quest_states import AttemptStatus
from app.models.evidence import Evidence
from app.models.quest_attempt import QuestAttempt
from app.repositories.evidence_repository import EvidenceRepository
from app.schemas.evidence import EvidenceUploadResponse
from app.schemas.sync import SyncMetadata
from app.storage.base import StorageProvider

logger = logging.getLogger(__name__)

_evidence_repo = EvidenceRepository()

# ---------------------------------------------------------------------------
# Allowed MIME types and their permitted file extensions
# ---------------------------------------------------------------------------

ALLOWED_MIME_TO_EXTENSIONS: dict[str, frozenset[str]] = {
    "image/jpeg": frozenset({".jpg", ".jpeg"}),
    "image/png": frozenset({".png"}),
    "image/webp": frozenset({".webp"}),
}

ALLOWED_MIME_TYPES: frozenset[str] = frozenset(ALLOWED_MIME_TO_EXTENSIONS.keys())

# Statuses that permit evidence upload
EVIDENCE_UPLOAD_STATES: frozenset[AttemptStatus] = frozenset(
    {
        AttemptStatus.RETURNED,
        AttemptStatus.EVIDENCE_PENDING,
    }
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _validate_mime_type(content_type: str) -> str:
    """Return the normalised MIME type or raise BadRequestException."""
    # Normalise: strip parameters like "; charset=utf-8"
    mime = content_type.split(";")[0].strip().lower()
    if mime not in ALLOWED_MIME_TYPES:
        raise BadRequestException(
            message=f"Unsupported file type '{mime}'. Allowed: {sorted(ALLOWED_MIME_TYPES)}",
            details={"mime_type": mime},
        )
    return mime


def _validate_extension(filename: str, mime_type: str) -> None:
    """Check the file extension is consistent with the declared MIME type."""
    if not filename:
        raise BadRequestException(message="Filename is required")

    # Guard against path traversal in filenames
    safe_name = filename.replace("/", "").replace("\\", "").replace("..", "")
    ext = ""
    if "." in safe_name:
        ext = "." + safe_name.rsplit(".", 1)[-1].lower()

    allowed_exts = ALLOWED_MIME_TO_EXTENSIONS.get(mime_type, frozenset())
    if ext not in allowed_exts:
        raise BadRequestException(
            message=f"File extension '{ext}' is not valid for MIME type '{mime_type}'. "
            f"Expected one of: {sorted(allowed_exts)}",
            details={"extension": ext, "mime_type": mime_type},
        )


def _validate_image_bytes(data: bytes, mime_type: str) -> None:
    """Attempt to decode the image with Pillow to confirm it is a real image.

    This guards against executables or malicious files that have been
    given a valid image extension/MIME type.
    """
    try:
        import io

        from PIL import Image

        img = Image.open(io.BytesIO(data))
        img.verify()  # raises on corrupt/invalid images
    except ImportError:
        # Pillow not installed — skip decode validation, log warning
        logger.warning(
            "Pillow not installed — skipping image decode validation. "
            "Install Pillow for full security."
        )
    except Exception as exc:
        raise BadRequestException(
            message="File failed image decode validation — it may be corrupt or not a real image.",
            details={"error": str(exc)},
        ) from exc


def _compute_checksum(data: bytes) -> str:
    """Return the SHA-256 hex digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def _generate_storage_key(mime_type: str, attempt_id: UUID) -> str:
    """Generate a random, opaque storage key.

    Format: evidence/{attempt_id}/{random_uuid}.{ext}
    The random UUID prevents enumeration; the attempt_id prefix groups
    evidence for the same attempt in object storage.
    """
    ext_map = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }
    ext = ext_map.get(mime_type, "bin")
    return f"evidence/{attempt_id}/{uuid.uuid4()}.{ext}"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


async def upload_evidence(
    db: AsyncSession,
    *,
    user_id: UUID,
    attempt_id: UUID,
    file_data: bytes,
    filename: str,
    content_type: str,
    storage: StorageProvider,
    idempotency_key: str | None = None,
) -> EvidenceUploadResponse:
    """Validate, store, and persist an evidence upload.

    Args:
        db:           Active async DB session.
        user_id:      Authenticated user performing the upload.
        attempt_id:   QuestAttempt the evidence belongs to.
        file_data:    Raw bytes of the uploaded file (read completely before call).
        filename:     Original filename from the multipart upload.
        content_type: MIME type declared by the client.
        storage:      StorageProvider to persist the file.

    Returns:
        EvidenceUploadResponse with safe metadata (no paths).

    Raises:
        NotFoundException    – attempt not found.
        ForbiddenException   – attempt belongs to another user.
        BadRequestException  – wrong state, oversized, invalid MIME, bad extension,
                               failed image decode.
    """
    settings = get_settings()

    # ── 1. Size check (fast-fail before any DB or storage I/O) ──────────────
    size = len(file_data)
    if size == 0:
        raise BadRequestException(message="Uploaded file is empty")
    if size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
        raise BadRequestException(
            message=f"File too large. Maximum allowed size is {max_mb:.0f} MB "
            f"(got {size / (1024 * 1024):.2f} MB).",
            details={"size_bytes": size, "max_bytes": settings.MAX_UPLOAD_SIZE_BYTES},
        )

    # ── 2. MIME type validation ──────────────────────────────────────────────
    mime_type = _validate_mime_type(content_type)

    # ── 3. Extension validation ──────────────────────────────────────────────
    _validate_extension(filename, mime_type)

    # ── 4. Image decode validation ───────────────────────────────────────────
    _validate_image_bytes(file_data, mime_type)

    # ── 5. Attempt ownership and state ──────────────────────────────────────
    result = await db.execute(select(QuestAttempt).where(QuestAttempt.id == attempt_id))
    attempt = result.scalar_one_or_none()
    if attempt is None:
        raise NotFoundException(message="Quest attempt not found")
    if attempt.user_id != user_id:
        raise ForbiddenException(message="You do not own this quest attempt")

    current_status = AttemptStatus(attempt.status)
    if current_status not in EVIDENCE_UPLOAD_STATES:
        raise BadRequestException(
            message=(
                f"Evidence cannot be uploaded when the attempt is in '{current_status}' state. "
                f"Allowed states: {sorted(s.value for s in EVIDENCE_UPLOAD_STATES)}"
            ),
            details={
                "current_status": current_status.value,
                "allowed_states": sorted(s.value for s in EVIDENCE_UPLOAD_STATES),
            },
        )

    # ── 6. Checksum and storage key ──────────────────────────────────────────
    checksum = _compute_checksum(file_data)
    storage_key = _generate_storage_key(mime_type, attempt_id)

    # ── 7. Persist to storage ────────────────────────────────────────────────
    upload_result = await storage.upload(
        data=file_data,
        key=storage_key,
        content_type=mime_type,
    )

    logger.info(
        "Evidence stored",
        extra={
            "event": "evidence_processing",
            "attempt_id": str(attempt_id),
            "size_bytes": size,
            "mime_type": mime_type,
            "storage_key": storage_key,
            "action": "storage_upload_success",
        },
    )

    # ── 8. Persist metadata to DB ────────────────────────────────────────────
    evidence = Evidence(
        attempt_id=attempt_id,
        storage_key=upload_result.storage_key,
        mime_type=mime_type,
        size_bytes=upload_result.size_bytes,
        checksum=checksum,
    )
    created = await _evidence_repo.create(db, evidence)

    logger.info(
        "Evidence record created",
        extra={
            "event": "evidence_processing",
            "evidence_id": str(created.id),
            "attempt_id": str(attempt_id),
            "action": "db_record_created",
        },
    )

    # ── 9. State Transition ──────────────────────────────────────────────────
    if current_status == AttemptStatus.RETURNED:
        from app.services import quest_service

        await quest_service.mark_evidence_pending(db, user_id, attempt.quest_id)

    return EvidenceUploadResponse(
        evidence_id=str(created.id),
        attempt_id=str(created.attempt_id),
        status="uploaded",
        mime_type=created.mime_type,
        size_bytes=created.size_bytes,
        checksum=created.checksum,
        created_at=created.created_at,
        sync=SyncMetadata(
            server_timestamp=datetime.now(UTC),
            resource_version=str(created.id),
            idempotency_key=idempotency_key,
        ),
    )
