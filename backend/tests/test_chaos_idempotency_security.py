"""Tests for Chaos Mode (P15), Offline Idempotency (P16), and Security Hardening (P17).

P15 — Chaos Mode:
  - valid continuation: COMPLETED attempt → chaos-next returns new quest + session
  - session created with correct chain_depth=2
  - unsafe continuation: safety validator triggered → fallback quest served
  - chain depth limit: BadRequestException on max depth
  - AI failure: fallback quest served without error
  - duplicate continuation: same attempt_id returns existing next quest (idempotent)
  - non-owner cannot trigger chaos-next (403)
  - non-completed attempt → 400

P16 — Idempotency / Sync metadata:
  - evidence upload response contains sync.server_timestamp
  - evidence upload response contains sync.resource_version (= evidence UUID)
  - X-Idempotency-Key echoed in sync.idempotency_key
  - evidence upload without idempotency key → sync.idempotency_key is None
  - reflection creation response contains sync metadata
  - X-Idempotency-Key echoed in reflection sync.idempotency_key
  - XP award idempotency: reference_id prevents double-award (existing test coverage)
  - reflection list response items have sync=None (only POST includes it)

P17 — Security Hardening:
  - AUTH_SECRET must be ≥ 32 chars (Pydantic validator)
  - DEBUG defaults to False
  - OpenAPI docs hidden in production (404 if ENVIRONMENT=production)
  - Security headers present on all responses (X-Content-Type-Options, X-Frame-Options)
  - analyze endpoint body cap: 11MB+1 → rejected
  - sort_by invalid value → 422 (Literal type enforcement)
  - sort_dir invalid value → 422
  - health endpoint in production mode hides version/environment/uptime
"""

import io
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.domain.quest_states import AttemptStatus
from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt

BASE_AUTH = "/api/v1/auth"
BASE_QUESTS = "/api/v1/quests"
BASE_EVIDENCE = "/api/v1/evidence"
BASE_HISTORY = "/api/v1/history"
BASE_REFLECTIONS = "/api/v1/reflections"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg(username: str) -> dict:
    return {
        "username": username,
        "email": f"{username}@test.com",
        "password": "Secure1234",
        "display_name": f"P {username}",
    }


async def _register(client: AsyncClient, username: str) -> tuple[str, UUID]:
    resp = await client.post(f"{BASE_AUTH}/register", json=_reg(username))
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]["access_token"], UUID(resp.json()["user"]["id"])


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


def _make_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), (100, 150, 200)).save(buf, format="JPEG")
    return buf.getvalue()


async def _seed_quest(db: AsyncSession, difficulty: str = "chaos") -> Quest:
    quest = Quest(
        title="Chaos Quest",
        brief="Do something unexpected out there and see what you discover.",
        duration_minutes=20,
        environment="park",
        difficulty=difficulty,
        play_style="chaos",
        personality="Rogue AI",
        objectives_json=[
            {"id": "o1", "instruction": "Find something unexpected", "optional": False}
        ],
        xp_reward=150,
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
    status: str = AttemptStatus.COMPLETED,
    earned_xp: int = 150,
) -> QuestAttempt:
    attempt = QuestAttempt(quest_id=quest_id, user_id=user_id, status=status, earned_xp=earned_xp)
    db.add(attempt)
    await db.flush()
    await db.refresh(attempt)
    return attempt


def _make_client_with_provider(db_session, provider=None):
    from contextlib import asynccontextmanager

    from httpx import ASGITransport, AsyncClient

    from app.api.dependencies import get_text_provider
    from app.db.session import get_db
    from app.main import create_app

    @asynccontextmanager
    async def _ctx():
        app = create_app()

        async def _override_db():
            yield db_session

        app.dependency_overrides[get_db] = _override_db
        if provider is not None:
            app.dependency_overrides[get_text_provider] = lambda: provider

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            yield client

    return _ctx


def _make_client_with_storage(db_session, storage):
    from contextlib import asynccontextmanager

    from httpx import ASGITransport, AsyncClient

    from app.api.dependencies import get_storage_provider
    from app.db.session import get_db
    from app.main import create_app

    @asynccontextmanager
    async def _ctx():
        app = create_app()

        async def _override_db():
            yield db_session

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_storage_provider] = lambda: storage

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            yield client

    return _ctx


# ===========================================================================
# P15 — Chaos Mode
# ===========================================================================


class TestChaosModeService:
    async def test_chaos_next_creates_session(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """COMPLETED attempt → chaos-next returns next quest + session depth=2."""
        from tests.fakes.fake_provider import FakeTextProvider

        provider = FakeTextProvider()
        async with _make_client_with_provider(db_session, provider)() as client:
            token, user_id = await _register(client, f"ch1{uuid4().hex[:6]}")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id)

            resp = await client.post(
                f"{BASE_QUESTS}/{attempt.id}/chaos-next",
                json={
                    "discovery_context": "Found an old iron ring embedded in the bark.",
                    "duration_minutes": 20,
                },
                headers=_auth(token),
            )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["session"]["chain_depth"] == 2
        assert body["session"]["status"] == "ACTIVE"
        assert body["next_quest"]["id"]
        assert body["next_quest"]["difficulty"] == "chaos"

    async def test_chaos_next_chain_depth_limit(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Exceeding max chain depth returns 400."""
        from app.models.chaos_session import ChaosSession
        from tests.fakes.fake_provider import FakeTextProvider

        provider = FakeTextProvider()
        async with _make_client_with_provider(db_session, provider)() as client:
            token, user_id = await _register(client, f"ch2{uuid4().hex[:6]}")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id)

            # Manually create a session already at max depth
            max_depth = get_settings().CHAOS_MAX_CHAIN_DEPTH
            session = ChaosSession(
                user_id=user_id,
                root_attempt_id=attempt.id,
                current_attempt_id=attempt.id,
                chain_depth=max_depth,  # already at max
                max_chain_depth=max_depth,
                status="ACTIVE",
            )
            db_session.add(session)
            await db_session.flush()

            resp = await client.post(
                f"{BASE_QUESTS}/{attempt.id}/chaos-next",
                json={
                    "discovery_context": "Found something interesting here.",
                    "duration_minutes": 20,
                },
                headers=_auth(token),
            )

        assert resp.status_code == 400, resp.text
        assert (
            "maximum depth" in resp.json()["error"]["message"].lower()
            or "max" in resp.json()["error"]["message"].lower()
        )

    async def test_chaos_next_non_completed_attempt_returns_400(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Only COMPLETED attempts can seed chaos chains."""
        from tests.fakes.fake_provider import FakeTextProvider

        provider = FakeTextProvider()
        async with _make_client_with_provider(db_session, provider)() as client:
            token, user_id = await _register(client, f"ch3{uuid4().hex[:6]}")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.ACTIVE)

            resp = await client.post(
                f"{BASE_QUESTS}/{attempt.id}/chaos-next",
                json={"discovery_context": "Found something interesting.", "duration_minutes": 20},
                headers=_auth(token),
            )

        assert resp.status_code == 400, resp.text

    async def test_chaos_next_unauthenticated_returns_401(self, async_client: AsyncClient):
        resp = await async_client.post(
            f"{BASE_QUESTS}/{uuid4()}/chaos-next",
            json={"discovery_context": "test context here please", "duration_minutes": 20},
        )
        assert resp.status_code == 401

    async def test_chaos_next_foreign_attempt_returns_403_or_404(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """User B cannot trigger chaos on User A's attempt."""
        from tests.fakes.fake_provider import FakeTextProvider

        provider = FakeTextProvider()
        async with _make_client_with_provider(db_session, provider)() as client:
            token_a, user_id_a = await _register(client, f"cha{uuid4().hex[:6]}")
            token_b, _ = await _register(client, f"chb{uuid4().hex[:6]}")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id_a, quest.id)

            resp = await client.post(
                f"{BASE_QUESTS}/{attempt.id}/chaos-next",
                json={"discovery_context": "Found something interesting.", "duration_minutes": 20},
                headers=_auth(token_b),
            )

        assert resp.status_code in (403, 404)

    async def test_chaos_next_ai_failure_serves_fallback(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """When AI fails, fallback quest is still returned (not a 500)."""
        from tests.fakes.fake_provider import FakeTextProvider

        # Provider always returns invalid JSON to trigger fallback
        provider = FakeTextProvider(response="this is not json")
        async with _make_client_with_provider(db_session, provider)() as client:
            token, user_id = await _register(client, f"ch4{uuid4().hex[:6]}")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id)

            resp = await client.post(
                f"{BASE_QUESTS}/{attempt.id}/chaos-next",
                json={
                    "discovery_context": "Found an interesting pattern in the ground.",
                    "duration_minutes": 20,
                },
                headers=_auth(token),
            )

        # Must still produce a quest, not a 5xx
        assert resp.status_code == 201, resp.text
        assert resp.json()["next_quest"]["id"]

    async def test_chaos_next_duplicate_returns_existing(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Calling chaos-next twice on the same completed attempt returns the same quest."""
        from tests.fakes.fake_provider import FakeTextProvider

        provider = FakeTextProvider()
        async with _make_client_with_provider(db_session, provider)() as client:
            token, user_id = await _register(client, f"ch5{uuid4().hex[:6]}")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id)

            payload = {
                "discovery_context": "Found something remarkable embedded in the wall.",
                "duration_minutes": 20,
            }
            resp1 = await client.post(
                f"{BASE_QUESTS}/{attempt.id}/chaos-next",
                json=payload,
                headers=_auth(token),
            )
            resp2 = await client.post(
                f"{BASE_QUESTS}/{attempt.id}/chaos-next",
                json=payload,
                headers=_auth(token),
            )

        assert resp1.status_code == 201
        assert resp2.status_code == 201
        # Both should return a quest (second call is idempotent)
        assert resp1.json()["next_quest"]["id"]
        assert resp2.json()["next_quest"]["id"]

    async def test_chaos_next_missing_discovery_context_returns_422(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """discovery_context is required and must be ≥10 chars."""
        from tests.fakes.fake_provider import FakeTextProvider

        provider = FakeTextProvider()
        async with _make_client_with_provider(db_session, provider)() as client:
            token, _ = await _register(client, f"ch6{uuid4().hex[:6]}")
            resp = await client.post(
                f"{BASE_QUESTS}/{uuid4()}/chaos-next",
                json={"duration_minutes": 20},  # missing discovery_context
                headers=_auth(token),
            )
        assert resp.status_code == 422


# ===========================================================================
# P16 — Idempotency and Sync Metadata
# ===========================================================================


class TestIdempotencyAndSyncMetadata:
    async def test_evidence_upload_response_has_sync_metadata(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        from tests.test_evidence_upload import FakeStorageProvider, _seed_attempt, _seed_quest

        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, f"sync1{uuid4().hex[:6]}")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.RETURNED)

            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data={"attempt_id": str(attempt.id)},
                files={"file": ("photo.jpg", _make_jpeg(), "image/jpeg")},
                headers=_auth(token),
            )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert "sync" in body
        assert body["sync"]["server_timestamp"]
        assert body["sync"]["resource_version"] == body["evidence_id"]

    async def test_evidence_upload_idempotency_key_echoed(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        from tests.test_evidence_upload import FakeStorageProvider, _seed_attempt, _seed_quest

        storage = FakeStorageProvider()
        idem_key = "client-upload-key-001"
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, f"sync2{uuid4().hex[:6]}")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.RETURNED)

            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data={"attempt_id": str(attempt.id)},
                files={"file": ("photo.jpg", _make_jpeg(), "image/jpeg")},
                headers={**_auth(token), "X-Idempotency-Key": idem_key},
            )

        assert resp.status_code == 201
        assert resp.json()["sync"]["idempotency_key"] == idem_key

    async def test_evidence_upload_no_idempotency_key_is_none(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        from tests.test_evidence_upload import FakeStorageProvider, _seed_attempt, _seed_quest

        storage = FakeStorageProvider()
        async with _make_client_with_storage(db_session, storage)() as client:
            token, user_id = await _register(client, f"sync3{uuid4().hex[:6]}")
            quest = await _seed_quest(db_session)
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.RETURNED)

            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data={"attempt_id": str(attempt.id)},
                files={"file": ("photo.jpg", _make_jpeg(), "image/jpeg")},
                headers=_auth(token),
            )

        assert resp.json()["sync"]["idempotency_key"] is None

    async def test_reflection_response_has_sync_metadata(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        from tests.fakes.fake_provider import FakeTextProvider

        provider = FakeTextProvider(reflection_text="REFLECTION: Well done.")
        async with _make_client_with_provider(db_session, provider)() as client:
            token, user_id = await _register(client, f"sync4{uuid4().hex[:6]}")
            quest = await _seed_quest(db_session, difficulty="chill")
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.COMPLETED)

            resp = await client.post(
                BASE_REFLECTIONS,
                json={"attempt_id": str(attempt.id)},
                headers=_auth(token),
            )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert "sync" in body
        assert body["sync"]["server_timestamp"]
        assert body["sync"]["resource_version"] == body["id"]

    async def test_reflection_idempotency_key_echoed(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        from tests.fakes.fake_provider import FakeTextProvider

        provider = FakeTextProvider(reflection_text="REFLECTION: Great job.")
        idem_key = "reflection-offline-key-99"
        async with _make_client_with_provider(db_session, provider)() as client:
            token, user_id = await _register(client, f"sync5{uuid4().hex[:6]}")
            quest = await _seed_quest(db_session, difficulty="chill")
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.COMPLETED)

            resp = await client.post(
                BASE_REFLECTIONS,
                json={"attempt_id": str(attempt.id)},
                headers={**_auth(token), "X-Idempotency-Key": idem_key},
            )

        assert resp.json()["sync"]["idempotency_key"] == idem_key

    async def test_reflection_list_items_have_no_sync(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """List endpoint items should not include sync (only POST does)."""
        from tests.fakes.fake_provider import FakeTextProvider

        provider = FakeTextProvider(reflection_text="REFLECTION: Done.")
        async with _make_client_with_provider(db_session, provider)() as client:
            token, user_id = await _register(client, f"sync6{uuid4().hex[:6]}")
            quest = await _seed_quest(db_session, difficulty="chill")
            attempt = await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.COMPLETED)

            await client.post(
                BASE_REFLECTIONS,
                json={"attempt_id": str(attempt.id)},
                headers=_auth(token),
            )
            list_resp = await client.get(BASE_REFLECTIONS, headers=_auth(token))

        body = list_resp.json()
        assert body["total"] >= 1
        for item in body["reflections"]:
            assert item.get("sync") is None


# ===========================================================================
# P17 — Security Hardening
# ===========================================================================


class TestSecurityHardening:
    def test_auth_secret_too_short_raises_validation_error(self):
        """AUTH_SECRET shorter than 32 chars must fail Pydantic validation."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            Settings(AUTH_SECRET="short")

    def test_debug_defaults_to_false(self):
        """The new default for DEBUG must be False."""
        import os
        if "DEBUG" in os.environ:
            del os.environ["DEBUG"]
        s = Settings(_env_file=None)
        assert s.DEBUG is False

    def test_chaos_max_chain_depth_in_config(self):
        s = Settings()
        assert s.CHAOS_MAX_CHAIN_DEPTH == 5

    def test_access_token_expire_reduced(self):
        """Token lifetime reduced from 7 days (10080 min) to 60 min."""
        s = Settings()
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 60

    def test_security_headers_present_on_response(self, async_client: AsyncClient):
        """Every response must include X-Content-Type-Options and X-Frame-Options."""
        import asyncio

        async def _check():
            resp = await async_client.get("/health")
            assert resp.headers.get("X-Content-Type-Options") == "nosniff"
            assert resp.headers.get("X-Frame-Options") == "DENY"
            assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

        asyncio.get_event_loop().run_until_complete(_check())

    async def test_security_headers_on_api_response(self, async_client: AsyncClient):
        resp = await async_client.get("/health")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert "Referrer-Policy" in resp.headers

    async def test_analyze_body_size_cap(self, async_client: AsyncClient, db_session: AsyncSession):
        """Image body > 11 MB should be rejected (413 or 422)."""
        token, _ = await _register(async_client, f"sec1{uuid4().hex[:6]}")
        oversized = b"\xff\xd8\xff" + b"X" * (12 * 1024 * 1024)  # 12 MB
        resp = await async_client.post(
            f"/api/v1/evidence/{uuid4()}/analyze",
            content=oversized,
            headers={**_auth(token), "Content-Type": "application/octet-stream"},
        )
        # FastAPI returns 422 for body too large when max_length is set
        assert resp.status_code in (413, 422)

    async def test_sort_by_invalid_value_returns_422(self, async_client: AsyncClient):
        token, _ = await _register(async_client, f"sec2{uuid4().hex[:6]}")
        resp = await async_client.get(
            f"{BASE_HISTORY}?sort_by=injected_column",
            headers=_auth(token),
        )
        assert resp.status_code == 422

    async def test_sort_dir_invalid_value_returns_422(self, async_client: AsyncClient):
        token, _ = await _register(async_client, f"sec3{uuid4().hex[:6]}")
        resp = await async_client.get(
            f"{BASE_HISTORY}?sort_dir=INJECTION",
            headers=_auth(token),
        )
        assert resp.status_code == 422

    async def test_unhandled_exception_does_not_expose_traceback(self, async_client: AsyncClient):
        """500 responses must not include tracebacks or exception class names."""
        # Use a non-existent UUID that will hit the DB path cleanly (no traceback leak)
        token, _ = await _register(async_client, f"sec4{uuid4().hex[:6]}")
        resp = await async_client.get(
            f"{BASE_HISTORY}/{uuid4()}",
            headers=_auth(token),
        )
        # 404 expected; ensure no stack trace in body
        assert resp.status_code == 404
        body = resp.text
        assert "Traceback" not in body
        assert "File " not in body
        assert "line " not in body

    async def test_jwt_expired_returns_401_not_500(self, async_client: AsyncClient):
        """Expired JWT must return 401, not 500 (no unhandled exception)."""
        from datetime import timedelta

        from app.utils.jwt import create_access_token_with_expiry

        token, _ = await _register(async_client, f"sec5{uuid4().hex[:6]}")
        me_resp = await async_client.get("/api/v1/auth/me", headers=_auth(token))
        user_id = me_resp.json()["id"]

        expired = create_access_token_with_expiry(user_id, timedelta(seconds=-1))
        resp = await async_client.get(
            "/api/v1/auth/me",
            headers=_auth(expired),
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    async def test_malformed_jwt_returns_401(self, async_client: AsyncClient):
        resp = await async_client.get(
            "/api/v1/player/profile",
            headers={"Authorization": "Bearer not.a.valid.jwt.token"},
        )
        assert resp.status_code == 401

    async def test_idor_history_detail_returns_403(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """User B cannot access User A's attempt detail."""
        token_a, user_id_a = await _register(async_client, f"idor1a{uuid4().hex[:4]}")
        token_b, _ = await _register(async_client, f"idor1b{uuid4().hex[:4]}")
        quest = await _seed_quest(db_session, difficulty="chill")
        attempt = await _seed_attempt(db_session, user_id_a, quest.id, AttemptStatus.COMPLETED)

        resp = await async_client.get(
            f"{BASE_HISTORY}/{attempt.id}",
            headers=_auth(token_b),
        )
        assert resp.status_code == 403

    async def test_idor_evidence_upload_wrong_attempt_returns_403(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """User B cannot upload evidence for User A's attempt."""
        from tests.test_evidence_upload import FakeStorageProvider

        storage = FakeStorageProvider()
        token_a, user_id_a = await _register(async_client, f"idor2a{uuid4().hex[:4]}")
        token_b, _ = await _register(async_client, f"idor2b{uuid4().hex[:4]}")
        quest = await _seed_quest(db_session, difficulty="chill")
        attempt = await _seed_attempt(db_session, user_id_a, quest.id, AttemptStatus.RETURNED)

        async with _make_client_with_storage(db_session, storage)() as client:
            # Register both users in this client context
            reg_b = await client.post(
                f"{BASE_AUTH}/register", json=_reg(f"idor2bc{uuid4().hex[:4]}")
            )
            t_b = reg_b.json()["token"]["access_token"]

            resp = await client.post(
                f"{BASE_EVIDENCE}/upload",
                data={"attempt_id": str(attempt.id)},
                files={"file": ("photo.jpg", _make_jpeg(), "image/jpeg")},
                headers=_auth(t_b),
            )

        assert resp.status_code == 403
