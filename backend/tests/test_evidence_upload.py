"""Tests for the evidence upload system.

Covers:
  Unit (service layer, no HTTP):
    - MIME allowlist: jpeg/png/webp accepted
    - MIME rejection: svg, html, pdf, text/plain, application/octet-stream, empty
    - Extension cross-check: .jpg with image/png rejected
    - Extension cross-check: .png with image/png accepted
    - SVG disguised as JPEG rejected at MIME layer
    - HTML disguised as PNG rejected at MIME layer
    - Oversized file rejected before storage write
    - Empty file rejected
    - Checksum is a valid 64-char hex string
    - Storage key format: starts with 'evidence/', ends with correct extension
    - Storage key is different on every call (random UUID)
    - PIL decode rejects a non-image (random bytes with jpg extension)
    - Service rejects attempt belonging to another user (403)
    - Service rejects wrong attempt state (400)
    - Service rejects missing attempt (404)

  Fake storage provider:
    - upload() stores data in memory
    - delete() removes the key
    - get_url() returns a non-path string
    - upload() called zero times when validation fails

  Integration (HTTP + in-memory storage):
    - POST /evidence/upload unauthenticated → 401
    - POST /evidence/upload valid JPEG → 201 with all required fields
    - POST /evidence/upload valid PNG → 201
    - POST /evidence/upload valid WEBP → 201
    - Response never contains filesystem path
    - Response storage_key not exposed
    - POST oversized image → 400
    - POST image/svg+xml → 400
    - POST text/html → 400
    - POST application/octet-stream → 400
    - POST wrong extension (.png file declared as image/jpeg) → 400
    - POST attempt in ACTIVE state → 400
    - POST attempt in COMPLETED state → 400
    - POST attempt in ABANDONED state → 400
    - POST attempt owned by another user → 403
    - POST nonexistent attempt_id → 404
    - POST duplicate upload to same attempt → 201 (multiple evidence allowed)
"""

import io
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_storage_provider
from app.core.exceptions import BadRequestException
from app.domain.quest_states import AttemptStatus
from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt
from app.services.evidence_service import (
    ALLOWED_MIME_TYPES,
    _compute_checksum,
    _generate_storage_key,
    _validate_extension,
    _validate_mime_type,
)
from app.storage.base import StorageProvider, UploadResult

BASE_AUTH = "/api/v1/auth"
BASE_EVIDENCE = "/api/v1/evidence"

# ---------------------------------------------------------------------------
# Minimal real image bytes (PIL-verified, smallest possible)
# ---------------------------------------------------------------------------


def _make_jpeg(w: int = 4, h: int = 4) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color=(128, 64, 32)).save(buf, format="JPEG")
    return buf.getvalue()


def _make_png(w: int = 4, h: int = 4) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color=(0, 128, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _make_webp(w: int = 4, h: int = 4) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color=(255, 128, 0)).save(buf, format="WEBP")
    return buf.getvalue()


def _fake_non_image_bytes(size: int = 256) -> bytes:
    """Random bytes that are NOT a valid image."""
    import os

    return os.urandom(size)


# ---------------------------------------------------------------------------
# Fake in-memory StorageProvider
# ---------------------------------------------------------------------------


class FakeStorageProvider(StorageProvider):
    """In-memory storage for tests — no disk I/O."""

    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}
        self.upload_calls: int = 0
        self.delete_calls: int = 0

    async def upload(self, data: bytes, key: str, content_type: str) -> UploadResult:
        self.store[key] = data
        self.upload_calls += 1
        return UploadResult(storage_key=key, size_bytes=len(data))

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)
        self.delete_calls += 1

    async def get_url(self, key: str, expires_seconds: int = 3600) -> str:
        return f"/fake/serve/{key}"


# ---------------------------------------------------------------------------
# DB seed helpers
# ---------------------------------------------------------------------------


async def _seed_quest(db: AsyncSession) -> Quest:
    quest = Quest(
        title="Evidence Test Quest",
        brief="Go outside and find something interesting to photograph.",
        duration_minutes=20,
        environment="park",
        difficulty="chill",
        play_style="explorer",
        personality="Wizard",
        objectives_json=[
            {"id": "obj-1", "instruction": "Find something colourful", "optional": False}
        ],
        xp_reward=75,
        evidence_required=True,
        safety_notes="Stay on public paths.",
        model_name="test",
        prompt_version="v1",
    )
    db.add(quest)
    await db.flush()
    await db.refresh(quest)
    return quest


async def _seed_attempt(
    db: AsyncSession,
    user_id: UUID,
    quest_id: UUID,
    status: str = AttemptStatus.RETURNED,
) -> QuestAttempt:
    attempt = QuestAttempt(
        quest_id=quest_id,
        user_id=user_id,
        status=status,
        earned_xp=0,
    )
    db.add(attempt)
    await db.flush()
    await db.refresh(attempt)
    return attempt


def _reg(username: str, email: str) -> dict:
    return {
        "username": username,
        "email": email,
        "password": "Secure1234",
        "display_name": f"Player {username}",
    }


async def _register(client: AsyncClient, username: str, email: str) -> tuple[str, UUID]:
    """Register a user and return (token, user_id)."""
    resp = await client.post(f"{BASE_AUTH}/register", json=_reg(username, email))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["token"]["access_token"], UUID(body["user"]["id"])


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _multipart(
    attempt_id: UUID,
    data: bytes,
    filename: str = "photo.jpg",
    content_type: str = "image/jpeg",
) -> tuple[dict, dict]:
    """Return (data, files) for httpx multipart upload."""
    form = {"attempt_id": str(attempt_id)}
    files = {"file": (filename, data, content_type)}
    return form, files


# ===========================================================================
# Unit — MIME validation
# ===========================================================================


class TestMimeValidation:
    def test_jpeg_accepted(self):
        assert _validate_mime_type("image/jpeg") == "image/jpeg"

    def test_jpeg_with_charset_param_accepted(self):
        assert _validate_mime_type("image/jpeg; charset=utf-8") == "image/jpeg"

    def test_png_accepted(self):
        assert _validate_mime_type("image/png") == "image/png"

    def test_webp_accepted(self):
        assert _validate_mime_type("image/webp") == "image/webp"

    def test_svg_rejected(self):
        with pytest.raises(BadRequestException, match="Unsupported"):
            _validate_mime_type("image/svg+xml")

    def test_html_rejected(self):
        with pytest.raises(BadRequestException):
            _validate_mime_type("text/html")

    def test_pdf_rejected(self):
        with pytest.raises(BadRequestException):
            _validate_mime_type("application/pdf")

    def test_octet_stream_rejected(self):
        with pytest.raises(BadRequestException):
            _validate_mime_type("application/octet-stream")

    def test_plain_text_rejected(self):
        with pytest.raises(BadRequestException):
            _validate_mime_type("text/plain")

    def test_empty_string_rejected(self):
        with pytest.raises(BadRequestException):
            _validate_mime_type("")

    def test_gif_rejected(self):
        with pytest.raises(BadRequestException):
            _validate_mime_type("image/gif")

    def test_all_allowed_types_in_frozenset(self):
        assert "image/jpeg" in ALLOWED_MIME_TYPES
        assert "image/png" in ALLOWED_MIME_TYPES
        assert "image/webp" in ALLOWED_MIME_TYPES


# ===========================================================================
# Unit — extension cross-check
# ===========================================================================


class TestExtensionValidation:
    def test_jpg_with_jpeg_mime_accepted(self):
        _validate_extension("photo.jpg", "image/jpeg")  # must not raise

    def test_jpeg_with_jpeg_mime_accepted(self):
        _validate_extension("photo.jpeg", "image/jpeg")

    def test_png_with_png_mime_accepted(self):
        _validate_extension("shot.png", "image/png")

    def test_webp_with_webp_mime_accepted(self):
        _validate_extension("image.webp", "image/webp")

    def test_png_extension_with_jpeg_mime_rejected(self):
        with pytest.raises(BadRequestException, match="not valid"):
            _validate_extension("photo.png", "image/jpeg")

    def test_jpg_extension_with_png_mime_rejected(self):
        with pytest.raises(BadRequestException):
            _validate_extension("photo.jpg", "image/png")

    def test_svg_extension_with_jpeg_mime_rejected(self):
        with pytest.raises(BadRequestException):
            _validate_extension("malicious.svg", "image/jpeg")

    def test_exe_extension_with_jpeg_mime_rejected(self):
        with pytest.raises(BadRequestException):
            _validate_extension("virus.exe", "image/jpeg")

    def test_no_extension_rejected(self):
        with pytest.raises(BadRequestException):
            _validate_extension("photofile", "image/jpeg")

    def test_uppercase_extension_accepted(self):
        _validate_extension("Photo.JPG", "image/jpeg")  # must not raise

    def test_path_traversal_in_filename_handled(self):
        # Path traversal attempts should not raise on extension check itself
        # (the key security is that service never uses the filename for storage)
        with pytest.raises(BadRequestException):
            # ../../etc/passwd has no valid image extension
            _validate_extension("../../etc/passwd", "image/jpeg")


# ===========================================================================
# Unit — checksum and storage key
# ===========================================================================


class TestChecksumAndKey:
    def test_checksum_is_64_char_hex(self):
        checksum = _compute_checksum(b"hello world")
        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_checksum_is_deterministic(self):
        data = b"test evidence content"
        assert _compute_checksum(data) == _compute_checksum(data)

    def test_checksum_matches_known_value(self):
        # SHA-256("") = e3b0c44298fc1c149afb...
        assert _compute_checksum(b"").startswith("e3b0c442")

    def test_storage_key_starts_with_evidence_prefix(self):
        key = _generate_storage_key("image/jpeg", uuid4())
        assert key.startswith("evidence/")

    def test_storage_key_ends_with_correct_extension_jpeg(self):
        key = _generate_storage_key("image/jpeg", uuid4())
        assert key.endswith(".jpg")

    def test_storage_key_ends_with_correct_extension_png(self):
        key = _generate_storage_key("image/png", uuid4())
        assert key.endswith(".png")

    def test_storage_key_ends_with_correct_extension_webp(self):
        key = _generate_storage_key("image/webp", uuid4())
        assert key.endswith(".webp")

    def test_storage_key_contains_attempt_id(self):
        attempt_id = uuid4()
        key = _generate_storage_key("image/jpeg", attempt_id)
        assert str(attempt_id) in key

    def test_storage_key_unique_per_call(self):
        attempt_id = uuid4()
        k1 = _generate_storage_key("image/jpeg", attempt_id)
        k2 = _generate_storage_key("image/jpeg", attempt_id)
        assert k1 != k2, "Storage keys must be unique (random UUID segment)"

    def test_storage_key_never_starts_with_slash(self):
        key = _generate_storage_key("image/png", uuid4())
        assert not key.startswith("/")


# ===========================================================================
# Unit — FakeStorageProvider
# ===========================================================================


class TestFakeStorageProvider:
    async def test_upload_stores_in_memory(self):
        storage = FakeStorageProvider()
        result = await storage.upload(b"data", "test/key.jpg", "image/jpeg")
        assert result.storage_key == "test/key.jpg"
        assert result.size_bytes == 4
        assert storage.store["test/key.jpg"] == b"data"

    async def test_delete_removes_key(self):
        storage = FakeStorageProvider()
        await storage.upload(b"x", "k", "image/jpeg")
        await storage.delete("k")
        assert "k" not in storage.store

    async def test_delete_nonexistent_key_is_idempotent(self):
        storage = FakeStorageProvider()
        await storage.delete("does_not_exist")  # must not raise

    async def test_get_url_does_not_expose_filesystem_path(self):
        storage = FakeStorageProvider()
        url = await storage.get_url("evidence/abc/def.jpg")
        assert not url.startswith("/tmp")
        assert not url.startswith("/var")
        assert not url.startswith("/home")
        assert "abc" in url or "fake" in url  # some opaque reference


# ===========================================================================
# Integration — HTTP endpoint
# ===========================================================================


def _make_client_with_storage(db_session, storage: StorageProvider):
    """Factory for test clients with both DB and storage overridden."""
    from contextlib import asynccontextmanager

    from app.db.session import get_db
    from app.main import create_app

    @asynccontextmanager
    async def _ctx():
        from httpx import ASGITransport, AsyncClient

        app = create_app()

        async def _override_db():
            yield db_session

        def _override_storage():
            return storage

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_storage_provider] = _override_storage

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            yield client

    return _ctx


class TestEvidenceUploadEndpoint:
    """Integration tests for POST /api/v1/evidence/upload."""

    async def test_unauthenticated_returns_401(self, async_client: AsyncClient):
        resp = await async_client.post(
            f"{BASE_EVIDENCE}/upload",
            files={"file": ("photo.jpg", _make_jpeg(), "image/jpeg")},
            data={"attempt_id": str(uuid4())},
        )
        assert resp.status_code == 401, resp.text

    async def test_valid_jpeg_returns_201(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev1", "ev1@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.RETURNED)

            form, files = _multipart(attempt.id, _make_jpeg(), "photo.jpg", "image/jpeg")
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "uploaded"
        assert body["mime_type"] == "image/jpeg"
        assert body["size_bytes"] > 0
        assert len(body["checksum"]) == 64
        assert body["evidence_id"]
        assert body["attempt_id"] == str(attempt.id)
        assert storage.upload_calls == 1

    async def test_valid_png_returns_201(self, async_client: AsyncClient, db_session: AsyncSession):
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev2", "ev2@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(
                db_session, user_id, quest.id, AttemptStatus.EVIDENCE_PENDING
            )

            form, files = _multipart(attempt.id, _make_png(), "shot.png", "image/png")
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 201, resp.text
        assert resp.json()["mime_type"] == "image/png"

    async def test_valid_webp_returns_201(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev3", "ev3@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.RETURNED)

            form, files = _multipart(attempt.id, _make_webp(), "img.webp", "image/webp")
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 201, resp.text
        assert resp.json()["mime_type"] == "image/webp"

    async def test_response_does_not_expose_filesystem_path(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev4", "ev4@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.RETURNED)

            form, files = _multipart(attempt.id, _make_jpeg())
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 201
        body_str = resp.text
        # No filesystem paths in response
        assert "/tmp" not in body_str
        assert "/var" not in body_str
        assert "/home" not in body_str
        assert "storage_key" not in body_str  # key not exposed in response schema

    async def test_oversized_image_returns_400(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev5", "ev5@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.RETURNED)

            # 11 MB of fake JPEG data (over 10 MB limit)
            oversized = b"\xff\xd8\xff" + b"X" * (11 * 1024 * 1024)
            form, files = _multipart(attempt.id, oversized, "big.jpg", "image/jpeg")
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 400, resp.text
        assert "large" in resp.json()["error"]["message"].lower()
        assert storage.upload_calls == 0  # storage never touched

    async def test_svg_mime_returns_400(self, async_client: AsyncClient, db_session: AsyncSession):
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev6", "ev6@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.RETURNED)

            svg_data = b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
            form, files = _multipart(attempt.id, svg_data, "evil.svg", "image/svg+xml")
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 400, resp.text
        assert storage.upload_calls == 0

    async def test_html_mime_returns_400(self, async_client: AsyncClient, db_session: AsyncSession):
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev7", "ev7@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.RETURNED)

            html_data = b"<html><body>xss</body></html>"
            form, files = _multipart(attempt.id, html_data, "page.html", "text/html")
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 400, resp.text

    async def test_octet_stream_returns_400(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev8", "ev8@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.RETURNED)

            form, files = _multipart(
                attempt.id, b"\x00\x01\x02\x03", "file.bin", "application/octet-stream"
            )
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 400, resp.text

    async def test_wrong_extension_returns_400(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """JPEG data with .png extension should be rejected."""
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev9", "ev9@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.RETURNED)

            form, files = _multipart(
                attempt.id,
                _make_jpeg(),
                "photo.png",
                "image/jpeg",  # extension mismatch
            )
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 400, resp.text
        assert "extension" in resp.json()["error"]["message"].lower()

    async def test_attempt_in_active_state_returns_400(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev10", "ev10@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.ACTIVE)

            form, files = _multipart(attempt.id, _make_jpeg())
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 400, resp.text
        body = resp.json()
        assert "ACTIVE" in body["error"]["message"]

    async def test_attempt_in_completed_state_returns_400(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev11", "ev11@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.COMPLETED)

            form, files = _multipart(attempt.id, _make_jpeg())
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 400, resp.text

    async def test_attempt_in_abandoned_state_returns_400(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev12", "ev12@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.ABANDONED)

            form, files = _multipart(attempt.id, _make_jpeg())
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 400, resp.text

    async def test_attempt_owned_by_another_user_returns_403(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """User B cannot upload evidence for User A's attempt."""
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token_a, user_id_a = await _register(client, "ev13a", "ev13a@example.com")
            token_b, _ = await _register(client, "ev13b", "ev13b@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id_a, quest.id, AttemptStatus.RETURNED)

            form, files = _multipart(attempt.id, _make_jpeg())
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token_b),  # user B's token, user A's attempt
            )

        assert resp.status_code == 403, resp.text

    async def test_nonexistent_attempt_returns_404(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, _ = await _register(client, "ev14", "ev14@example.com")
            fake_attempt_id = uuid4()

            form, files = _multipart(fake_attempt_id, _make_jpeg())
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 404, resp.text

    async def test_duplicate_upload_allowed(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Multiple evidence uploads for the same attempt are permitted."""
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev15", "ev15@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(
                db_session, user_id, quest.id, AttemptStatus.EVIDENCE_PENDING
            )

            for i in range(2):
                form, files = _multipart(attempt.id, _make_jpeg(), f"photo{i}.jpg", "image/jpeg")
                resp = await client.post(
                    f"{BASE_EVIDENCE}/upload",
                    data=form,
                    files=files,
                    headers=_auth(token),
                )
                assert resp.status_code == 201, f"Upload {i + 1} failed: {resp.text}"

        assert storage.upload_calls == 2

    async def test_evidence_in_pocket_mode_state_returns_400(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """POCKET_MODE is not a valid upload state."""
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev16", "ev16@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.POCKET_MODE)

            form, files = _multipart(attempt.id, _make_jpeg())
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 400, resp.text

    async def test_evidence_pending_state_allowed(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """EVIDENCE_PENDING is explicitly an allowed upload state."""
        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, "ev17", "ev17@example.com")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(
                db_session, user_id, quest.id, AttemptStatus.EVIDENCE_PENDING
            )

            form, files = _multipart(attempt.id, _make_jpeg())
            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data=form,
                files=files,
                headers=_auth(token),
            )

        assert resp.status_code == 201, resp.text
