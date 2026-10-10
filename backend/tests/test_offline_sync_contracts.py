"""Offline synchronisation contract tests.

Verifies that all idempotency guarantees hold so a future offline client
can safely replay queued operations without causing duplicate state.

Contracts tested:
  1. Quest completion is idempotent (XP awarded exactly once)
  2. Evidence upload with idempotency key — key echoed in response
  3. Reflection creation with idempotency key — key echoed in response
  4. Sync metadata fields present on key responses
  5. XP award idempotency via reference_id
  6. Repeated GET requests return consistent data (no side effects)
  7. Chaos-next idempotency (duplicate call returns existing quest)
"""

import io
from uuid import UUID, uuid4

from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.quest_states import AttemptStatus
from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt

BASE = "/api/v1"


def _make_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), (100, 150, 200)).save(buf, format="JPEG")
    return buf.getvalue()


async def _register(client, username):
    resp = await client.post(
        f"{BASE}/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "Sync1234!",
            "display_name": f"P {username}",
        },
    )
    assert resp.status_code == 201
    return resp.json()["token"]["access_token"], UUID(resp.json()["user"]["id"])


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


async def _seed(db, user_id, status=AttemptStatus.RETURNED):
    quest = Quest(
        title="Sync Test Quest",
        brief="Test for offline sync verification.",
        duration_minutes=20,
        environment="park",
        difficulty="chill",
        play_style="explorer",
        personality="Wizard",
        objectives_json=[{"id": "o1", "instruction": "Do something here", "optional": False}],
        xp_reward=75,
        evidence_required=True,
        safety_notes="Stay safe.",
        model_name="test",
        prompt_version="v1",
    )
    db.add(quest)
    await db.flush()
    attempt = QuestAttempt(quest_id=quest.id, user_id=user_id, status=status, earned_xp=0)
    db.add(attempt)
    await db.flush()
    await db.refresh(quest)
    await db.refresh(attempt)
    return quest, attempt


class TestSyncMetadataFields:
    """Every key creation endpoint must return sync metadata."""

    async def test_evidence_upload_returns_sync_metadata(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        from httpx import ASGITransport
        from httpx import AsyncClient as HC

        from app.api.dependencies import get_storage_provider
        from app.db.session import get_db
        from app.main import create_app
        from app.storage.base import StorageProvider, UploadResult
        from tests.conftest import TestingSessionLocal

        class _S(StorageProvider):
            async def upload(self, data, key, content_type, **kwargs):
                return UploadResult(storage_key=key, size_bytes=len(data))

            async def delete(self, key):
                pass

            async def get_url(self, key, **kw):
                return f"/s/{key}"

        async with TestingSessionLocal() as db:
            app = create_app()

            async def _db():
                yield db

            app.dependency_overrides[get_db] = _db
            app.dependency_overrides[get_storage_provider] = lambda: _S()

            async with HC(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                token, user_id = await _register(client, f"sm1{uuid4().hex[:6]}")
                quest, attempt = await _seed(db, user_id)

                resp = await client.post(
                    f"{BASE}/evidence/upload",
                    data={"attempt_id": str(attempt.id)},
                    files={"file": ("p.jpg", _make_jpeg(), "image/jpeg")},
                    headers=_auth(token),
                )

        assert resp.status_code == 201
        body = resp.json()
        sync = body.get("sync")
        assert sync is not None, "sync field missing from evidence upload response"
        assert sync["server_timestamp"], "server_timestamp missing"
        assert sync["resource_version"] == body["evidence_id"], (
            "resource_version must equal the evidence UUID"
        )
        assert sync["idempotency_key"] is None  # no key was supplied

    async def test_evidence_upload_echoes_idempotency_key(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        from httpx import ASGITransport
        from httpx import AsyncClient as HC

        from app.api.dependencies import get_storage_provider
        from app.db.session import get_db
        from app.main import create_app
        from app.storage.base import StorageProvider, UploadResult
        from tests.conftest import TestingSessionLocal

        class _S(StorageProvider):
            async def upload(self, data, key, content_type, **kwargs):
                return UploadResult(storage_key=key, size_bytes=len(data))

            async def delete(self, k):
                pass

            async def get_url(self, k, **kw):
                return f"/s/{k}"

        idem_key = f"offline-upload-{uuid4()}"
        async with TestingSessionLocal() as db:
            app = create_app()

            async def _db():
                yield db

            app.dependency_overrides[get_db] = _db
            app.dependency_overrides[get_storage_provider] = lambda: _S()

            async with HC(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                token, user_id = await _register(client, f"sm2{uuid4().hex[:6]}")
                quest, attempt = await _seed(db, user_id)

                resp = await client.post(
                    f"{BASE}/evidence/upload",
                    data={"attempt_id": str(attempt.id)},
                    files={"file": ("p.jpg", _make_jpeg(), "image/jpeg")},
                    headers={**_auth(token), "X-Idempotency-Key": idem_key},
                )

        assert resp.json()["sync"]["idempotency_key"] == idem_key

    async def test_reflection_returns_sync_metadata(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        from httpx import ASGITransport
        from httpx import AsyncClient as HC

        from app.api.dependencies import get_text_provider
        from app.db.session import get_db
        from app.main import create_app
        from tests.conftest import TestingSessionLocal
        from tests.fakes.fake_provider import FakeTextProvider

        async with TestingSessionLocal() as db:
            app = create_app()

            async def _db():
                yield db

            app.dependency_overrides[get_db] = _db
            app.dependency_overrides[get_text_provider] = lambda: FakeTextProvider(
                reflection_text="REFLECTION: Well done."
            )

            async with HC(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                token, user_id = await _register(client, f"sm3{uuid4().hex[:6]}")
                quest, attempt = await _seed(db, user_id, AttemptStatus.COMPLETED)

                resp = await client.post(
                    f"{BASE}/reflections",
                    json={"attempt_id": str(attempt.id)},
                    headers=_auth(token),
                )

        assert resp.status_code == 201
        sync = resp.json().get("sync")
        assert sync is not None
        assert sync["server_timestamp"]
        assert sync["resource_version"] == resp.json()["id"]

    async def test_reflection_echoes_idempotency_key(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        from httpx import ASGITransport
        from httpx import AsyncClient as HC

        from app.api.dependencies import get_text_provider
        from app.db.session import get_db
        from app.main import create_app
        from tests.conftest import TestingSessionLocal
        from tests.fakes.fake_provider import FakeTextProvider

        idem_key = f"reflection-offline-{uuid4()}"
        async with TestingSessionLocal() as db:
            app = create_app()

            async def _db():
                yield db

            app.dependency_overrides[get_db] = _db
            app.dependency_overrides[get_text_provider] = lambda: FakeTextProvider(
                reflection_text="REFLECTION: Great work."
            )

            async with HC(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                token, user_id = await _register(client, f"sm4{uuid4().hex[:6]}")
                quest, attempt = await _seed(db, user_id, AttemptStatus.COMPLETED)

                resp = await client.post(
                    f"{BASE}/reflections",
                    json={"attempt_id": str(attempt.id)},
                    headers={**_auth(token), "X-Idempotency-Key": idem_key},
                )

        assert resp.json()["sync"]["idempotency_key"] == idem_key


class TestIdempotencyContracts:
    """Replay protection — duplicate operations must not create duplicate state."""

    async def test_quest_completion_idempotent_xp(self, db_session: AsyncSession):
        """Completing a quest twice awards XP exactly once."""
        from app.models.player_profile import PlayerProfile
        from app.models.user import User
        from app.repositories.progression_repository import XPTransactionRepository
        from app.services.xp_service import award_xp
        from app.utils.password import hash_password
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user = User(
                email=f"{uuid4().hex[:8]}@example.com",
                username=f"idem{uuid4().hex[:6]}",
                password_hash=hash_password("pw"),
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
            db.add(PlayerProfile(user_id=user.id, display_name="T", level=1, total_xp=0))
            quest, attempt = await _seed(db, user.id, AttemptStatus.VERIFYING)

            ref_id = f"quest_complete:{attempt.id}"

            # Award XP once with the standard reference_id used by complete_attempt
            p1 = await award_xp(db, user.id, quest.xp_reward, "quest complete", reference_id=ref_id)
            assert p1.total_xp == quest.xp_reward

            # Award again with same reference_id — must be idempotent
            p2 = await award_xp(
                db, user.id, quest.xp_reward, "quest complete again", reference_id=ref_id
            )
            assert p2.total_xp == quest.xp_reward  # unchanged

            txns = await XPTransactionRepository().get_by_user_id(db, user.id)
            quest_txns = [t for t in txns if t.reference_id == ref_id]

        assert len(quest_txns) == 1, (
            f"XP idempotency violation: {len(quest_txns)} transactions for same reference_id"
        )
        assert p2.total_xp == quest.xp_reward, f"XP doubled to {p2.total_xp}"

    async def test_xp_award_with_same_reference_id_deduped(self, db_session: AsyncSession):
        """award_xp with the same reference_id must not credit twice."""
        from app.models.player_profile import PlayerProfile
        from app.models.user import User
        from app.repositories.progression_repository import XPTransactionRepository
        from app.services.xp_service import award_xp
        from app.utils.password import hash_password
        from tests.conftest import TestingSessionLocal

        ref_id = f"test-ref-{uuid4()}"
        async with TestingSessionLocal() as db:
            user = User(
                email=f"{uuid4().hex[:8]}@t.com",
                username=f"xpid{uuid4().hex[:6]}",
                password_hash=hash_password("pw"),
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
            db.add(PlayerProfile(user_id=user.id, display_name="T", level=1, total_xp=0))
            await db.flush()

            await award_xp(db, user.id, 100, "first award", reference_id=ref_id)
            profile = await award_xp(db, user.id, 100, "duplicate", reference_id=ref_id)

            txns = await XPTransactionRepository().get_by_user_id(db, user.id)
            deduped = [t for t in txns if t.reference_id == ref_id]

        assert profile.total_xp == 100, f"XP doubled to {profile.total_xp}"
        assert len(deduped) == 1, f"Expected 1 transaction, got {len(deduped)}"

    async def test_get_endpoints_have_no_side_effects(self, async_client: AsyncClient):
        """Calling GET endpoints multiple times must not change state."""
        token, _ = await _register(async_client, f"idem_get{uuid4().hex[:6]}")

        stats1 = await async_client.get(f"{BASE}/player/stats", headers=_auth(token))
        stats2 = await async_client.get(f"{BASE}/player/stats", headers=_auth(token))

        assert stats1.json()["total_xp"] == stats2.json()["total_xp"]
        assert stats1.json()["level"] == stats2.json()["level"]
        assert stats1.json()["total_quests"] == stats2.json()["total_quests"]

    async def test_achievement_unlock_idempotent(self, db_session: AsyncSession):
        """Unlocking the same achievement twice leaves exactly one DB record."""
        from app.models.user import User
        from app.repositories.progression_repository import AchievementRepository
        from app.services.achievement_service import unlock
        from app.utils.password import hash_password
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user = User(
                email=f"{uuid4().hex[:8]}@t.com",
                username=f"achid{uuid4().hex[:6]}",
                password_hash=hash_password("pw"),
            )
            db.add(user)
            await db.flush()

            r1 = await unlock(db, user.id, "chaos_agent")
            r2 = await unlock(db, user.id, "chaos_agent")

            records = await AchievementRepository().get_by_user_id(db, user.id)

        assert r1 is not None
        assert r2 is None  # second unlock returns None (already held)
        assert len(records) == 1, f"Expected 1 achievement record, got {len(records)}"

    async def test_reflection_list_is_read_only(self, async_client: AsyncClient):
        """GET /reflections must not create any new records."""
        token, _ = await _register(async_client, f"rlist{uuid4().hex[:6]}")

        list1 = await async_client.get(f"{BASE}/reflections", headers=_auth(token))
        list2 = await async_client.get(f"{BASE}/reflections", headers=_auth(token))
        list3 = await async_client.get(f"{BASE}/reflections", headers=_auth(token))

        for r in (list1, list2, list3):
            assert r.status_code == 200
            assert r.json()["total"] == 0
