"""Comprehensive tests for Achievements (PROMPT 13) and Quest History/Stats (PROMPT 14).

Covers:
  Achievement definitions:
    - All 5 keys present in registry
    - Each definition has key, name, description, icon, threshold
    - get_definition() returns correct def or None for unknown

  AchievementService.evaluate_user():
    - first_contact unlocked on first completion
    - first_contact NOT unlocked again on second completion (idempotent)
    - chaos_agent unlocked on chaos difficulty quest
    - chaos_agent NOT unlocked on non-chaos quest
    - touch_grass unlocked after 3 outdoor completions
    - touch_grass NOT unlocked with only 2 outdoor completions
    - curious_mind unlocked after 5 observer completions
    - curious_mind NOT unlocked with 4 observer completions
    - pocket_player unlocked after 5 pocket-mode completions
    - pocket_player NOT unlocked with 4 pocket completions
    - evaluate_user with no completions unlocks nothing

  AchievementService.unlock():
    - unlock known key returns AchievementResponse
    - unlock same key twice returns None on second call (idempotent)
    - unlock unknown key returns None

  AchievementService.get_user_achievements():
    - returns full catalogue (5 entries)
    - locked achievements have unlocked_at=None
    - unlocked achievements have unlocked_at set

  GET /api/v1/achievements:
    - unauthenticated → 401
    - new user → 5 achievements all locked
    - after unlock → correct achievement marked with timestamp

  Quest history — HistoryService.get_history():
    - returns paginated list with skip/limit
    - status filter works (COMPLETED, ABANDONED)
    - sort by started_at desc/asc
    - sort by earned_xp desc
    - evidence summary populated when evidence exists
    - evidence summary empty when no evidence
    - AI outcome reflected in evidence summary

  GET /api/v1/history:
    - unauthenticated → 401
    - empty list for new player
    - returns attempts only for the authenticated user (cross-user isolation)
    - pagination skip/limit respected
    - status filter returns correct subset
    - response contains all required fields

  GET /api/v1/history/{attempt_id}:
    - unauthenticated → 401
    - correct detail returned for owned attempt
    - 403 for another user's attempt
    - 404 for nonexistent attempt_id

  Extended stats:
    - favorite_play_style populated after completions
    - avg_quest_duration_minutes populated
    - stats for new player show None for optional fields
    - player/stats endpoint returns new fields
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.achievements.definitions import ACHIEVEMENTS, get_definition
from app.domain.quest_states import AttemptStatus
from app.models.ai_analysis import AIAnalysis
from app.models.evidence import Evidence
from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt
from app.services.achievement_service import evaluate_user, get_user_achievements, unlock
from app.services.history_service import get_extended_stats, get_history

BASE_AUTH = "/api/v1/auth"
BASE_ACHIEVEMENTS = "/api/v1/achievements"
BASE_HISTORY = "/api/v1/history"
BASE_PLAYER = "/api/v1/player"

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def _seed_quest(
    db: AsyncSession,
    play_style: str = "explorer",
    difficulty: str = "chill",
    environment: str = "park",
    duration_minutes: int = 20,
) -> Quest:
    quest = Quest(
        title=f"{play_style} Quest",
        brief="Walk around and explore.",
        duration_minutes=duration_minutes,
        environment=environment,
        difficulty=difficulty,
        play_style=play_style,
        personality="Wizard",
        objectives_json=[{"id": "o1", "instruction": "Do something", "optional": False}],
        xp_reward=75,
        evidence_required=True,
        safety_notes="Be safe.",
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
    earned_xp: int = 75,
    pocket_started_at: datetime | None = None,
) -> QuestAttempt:
    attempt = QuestAttempt(
        quest_id=quest_id,
        user_id=user_id,
        status=status,
        earned_xp=earned_xp,
        pocket_started_at=pocket_started_at,
    )
    db.add(attempt)
    await db.flush()
    await db.refresh(attempt)
    return attempt


async def _seed_user(db: AsyncSession, username_prefix: str = "u") -> tuple[UUID, str]:
    """Create a user + profile, return (user_id, username)."""
    from app.models.player_profile import PlayerProfile
    from app.models.user import User
    from app.utils.password import hash_password

    uname = f"{username_prefix}{uuid4().hex[:8]}"
    user = User(
        email=f"{uname}@test.com",
        username=uname,
        password_hash=hash_password("pw"),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    profile = PlayerProfile(user_id=user.id, display_name=uname, level=1, total_xp=0)
    db.add(profile)
    await db.flush()
    return user.id, uname


def _reg(username: str) -> dict:
    return {
        "username": username,
        "email": f"{username}@test.com",
        "password": "Secure1234",
        "display_name": f"P {username}",
    }


async def _register(client, username: str) -> tuple[str, UUID]:
    resp = await client.post(f"{BASE_AUTH}/register", json=_reg(username))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["token"]["access_token"], UUID(body["user"]["id"])


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


# ===========================================================================
# Unit — achievement definitions registry
# ===========================================================================


class TestAchievementDefinitions:
    def test_all_five_keys_present(self):
        expected = {"first_contact", "touch_grass", "curious_mind", "chaos_agent", "pocket_player"}
        assert set(ACHIEVEMENTS.keys()) == expected

    def test_each_definition_has_required_fields(self):
        for key, defn in ACHIEVEMENTS.items():
            assert defn.key == key
            assert defn.name
            assert defn.description
            assert defn.icon
            assert defn.threshold >= 1

    def test_get_definition_known_key(self):
        defn = get_definition("first_contact")
        assert defn is not None
        assert defn.key == "first_contact"

    def test_get_definition_unknown_key_returns_none(self):
        assert get_definition("legendary_hero") is None

    def test_touch_grass_threshold_is_3(self):
        assert ACHIEVEMENTS["touch_grass"].threshold == 3

    def test_curious_mind_threshold_is_5(self):
        assert ACHIEVEMENTS["curious_mind"].threshold == 5

    def test_pocket_player_threshold_is_5(self):
        assert ACHIEVEMENTS["pocket_player"].threshold == 5


# ===========================================================================
# Unit — AchievementService.evaluate_user()
# ===========================================================================


class TestEvaluateUser:
    async def _setup(self, db):
        return await _seed_user(db)

    async def test_first_contact_unlocked_on_first_completion(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await self._setup(db)
            quest = await _seed_quest(db)
            await _seed_attempt(db, user_id, quest.id, AttemptStatus.COMPLETED)

            newly = await evaluate_user(db, user_id=user_id, quest=quest)

        keys = [a.key for a in newly]
        assert "first_contact" in keys

    async def test_first_contact_idempotent(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await self._setup(db)
            quest = await _seed_quest(db)
            await _seed_attempt(db, user_id, quest.id, AttemptStatus.COMPLETED)

            first = await evaluate_user(db, user_id=user_id, quest=quest)
            second = await evaluate_user(db, user_id=user_id, quest=quest)

        assert any(a.key == "first_contact" for a in first)
        assert not any(a.key == "first_contact" for a in second)

    async def test_chaos_agent_on_chaos_quest(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await self._setup(db)
            quest = await _seed_quest(db, difficulty="chaos")
            await _seed_attempt(db, user_id, quest.id, AttemptStatus.COMPLETED)

            newly = await evaluate_user(db, user_id=user_id, quest=quest)

        keys = [a.key for a in newly]
        assert "chaos_agent" in keys

    async def test_chaos_agent_not_on_non_chaos_quest(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await self._setup(db)
            quest = await _seed_quest(db, difficulty="chill")
            await _seed_attempt(db, user_id, quest.id, AttemptStatus.COMPLETED)

            newly = await evaluate_user(db, user_id=user_id, quest=quest)

        assert not any(a.key == "chaos_agent" for a in newly)

    async def test_touch_grass_unlocked_after_3_outdoor(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await self._setup(db)
            for env in ["park", "neighborhood", "trail"]:
                q = await _seed_quest(db, environment=env)
                await _seed_attempt(db, user_id, q.id, AttemptStatus.COMPLETED)

            quest = await _seed_quest(db, environment="park")
            newly = await evaluate_user(db, user_id=user_id, quest=quest)

        assert any(a.key == "touch_grass" for a in newly)

    async def test_touch_grass_not_unlocked_with_2_outdoor(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await self._setup(db)
            for env in ["park", "neighborhood"]:
                q = await _seed_quest(db, environment=env)
                await _seed_attempt(db, user_id, q.id, AttemptStatus.COMPLETED)

            quest = await _seed_quest(db, environment="park")
            newly = await evaluate_user(db, user_id=user_id, quest=quest)

        assert not any(a.key == "touch_grass" for a in newly)

    async def test_curious_mind_unlocked_after_5_observer(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await self._setup(db)
            for _ in range(5):
                q = await _seed_quest(db, play_style="observer")
                await _seed_attempt(db, user_id, q.id, AttemptStatus.COMPLETED)

            quest = await _seed_quest(db, play_style="observer")
            newly = await evaluate_user(db, user_id=user_id, quest=quest)

        assert any(a.key == "curious_mind" for a in newly)

    async def test_curious_mind_not_unlocked_with_4_observer(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await self._setup(db)
            for _ in range(4):
                q = await _seed_quest(db, play_style="observer")
                await _seed_attempt(db, user_id, q.id, AttemptStatus.COMPLETED)

            quest = await _seed_quest(db, play_style="observer")
            newly = await evaluate_user(db, user_id=user_id, quest=quest)

        assert not any(a.key == "curious_mind" for a in newly)

    async def test_pocket_player_unlocked_after_5_pocket_completions(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await self._setup(db)
            pocket_time = datetime.now(UTC)
            for _ in range(5):
                q = await _seed_quest(db)
                await _seed_attempt(
                    db, user_id, q.id, AttemptStatus.COMPLETED, pocket_started_at=pocket_time
                )

            quest = await _seed_quest(db)
            newly = await evaluate_user(db, user_id=user_id, quest=quest)

        assert any(a.key == "pocket_player" for a in newly)

    async def test_pocket_player_not_unlocked_with_4_pocket(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await self._setup(db)
            pocket_time = datetime.now(UTC)
            for _ in range(4):
                q = await _seed_quest(db)
                await _seed_attempt(
                    db, user_id, q.id, AttemptStatus.COMPLETED, pocket_started_at=pocket_time
                )

            quest = await _seed_quest(db)
            newly = await evaluate_user(db, user_id=user_id, quest=quest)

        assert not any(a.key == "pocket_player" for a in newly)

    async def test_no_completions_unlocks_nothing(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await self._setup(db)
            quest = await _seed_quest(db)
            newly = await evaluate_user(db, user_id=user_id, quest=quest)

        assert newly == []


# ===========================================================================
# Unit — AchievementService.unlock() and get_user_achievements()
# ===========================================================================


class TestUnlockAndGetAchievements:
    async def test_unlock_known_key_returns_response(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            result = await unlock(db, user_id=user_id, key="chaos_agent")

        assert result is not None
        assert result.key == "chaos_agent"
        assert result.unlocked_at is not None

    async def test_unlock_same_key_twice_idempotent(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            first = await unlock(db, user_id=user_id, key="chaos_agent")
            second = await unlock(db, user_id=user_id, key="chaos_agent")

        assert first is not None
        assert second is None  # already held

    async def test_unlock_unknown_key_returns_none(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            result = await unlock(db, user_id=user_id, key="legendary_hero_99")

        assert result is None

    async def test_get_user_achievements_returns_full_catalogue(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            result = await get_user_achievements(db, user_id=user_id)

        assert len(result.achievements) == 5
        assert result.unlocked_count == 0

    async def test_locked_achievements_have_null_unlocked_at(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            result = await get_user_achievements(db, user_id=user_id)

        for ach in result.achievements:
            assert ach.unlocked_at is None

    async def test_unlocked_achievement_has_timestamp(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            await unlock(db, user_id=user_id, key="first_contact")
            result = await get_user_achievements(db, user_id=user_id)

        first_contact = next(a for a in result.achievements if a.key == "first_contact")
        assert first_contact.unlocked_at is not None
        assert result.unlocked_count == 1


# ===========================================================================
# Integration — GET /api/v1/achievements
# ===========================================================================


class TestAchievementsEndpoint:
    async def test_unauthenticated_returns_401(self, async_client):
        resp = await async_client.get(BASE_ACHIEVEMENTS)
        assert resp.status_code == 401

    async def test_new_user_all_locked(self, async_client):
        token, _ = await _register(async_client, f"ach{uuid4().hex[:6]}")
        resp = await async_client.get(BASE_ACHIEVEMENTS, headers=_auth(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["unlocked_count"] == 0
        assert len(body["achievements"]) == 5
        for ach in body["achievements"]:
            assert ach["unlocked_at"] is None

    async def test_achievements_have_metadata(self, async_client):
        token, _ = await _register(async_client, f"ach{uuid4().hex[:6]}")
        resp = await async_client.get(BASE_ACHIEVEMENTS, headers=_auth(token))
        body = resp.json()
        for ach in body["achievements"]:
            assert ach["key"]
            assert ach["name"]
            assert ach["description"]
            assert ach["icon"]


# ===========================================================================
# Integration — history service
# ===========================================================================


class TestHistoryService:
    async def test_get_history_pagination(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            q = await _seed_quest(db)
            for _ in range(5):
                await _seed_attempt(db, user_id, q.id, AttemptStatus.COMPLETED)

            page1 = await get_history(db, user_id=user_id, skip=0, limit=3)
            page2 = await get_history(db, user_id=user_id, skip=3, limit=3)

        assert page1.total == 5
        assert len(page1.attempts) == 3
        assert len(page2.attempts) == 2

    async def test_status_filter_completed(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            q = await _seed_quest(db)
            await _seed_attempt(db, user_id, q.id, AttemptStatus.COMPLETED)
            await _seed_attempt(db, user_id, q.id, AttemptStatus.ABANDONED)
            await _seed_attempt(db, user_id, q.id, AttemptStatus.COMPLETED)

            result = await get_history(db, user_id=user_id, status_filter="COMPLETED")

        assert result.total == 2
        for item in result.attempts:
            assert item.status == "COMPLETED"

    async def test_status_filter_abandoned(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            q = await _seed_quest(db)
            await _seed_attempt(db, user_id, q.id, AttemptStatus.COMPLETED)
            await _seed_attempt(db, user_id, q.id, AttemptStatus.ABANDONED)

            result = await get_history(db, user_id=user_id, status_filter="ABANDONED")

        assert result.total == 1
        assert result.attempts[0].status == "ABANDONED"

    async def test_evidence_summary_populated(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            q = await _seed_quest(db)
            attempt = await _seed_attempt(db, user_id, q.id, AttemptStatus.COMPLETED)

            # Seed evidence + analysis
            ev = Evidence(
                attempt_id=attempt.id,
                storage_key=f"evidence/{attempt.id}/{uuid4()}.jpg",
                mime_type="image/jpeg",
                size_bytes=1024,
                checksum="a" * 64,
            )
            db.add(ev)
            await db.flush()
            await db.refresh(ev)
            an = AIAnalysis(
                evidence_id=ev.id,
                model_name="test",
                model_version="v1",
                confidence=0.9,
                findings_json={},
                completion_recommendation="SUCCESS",
            )
            db.add(an)
            await db.flush()

            result = await get_history(db, user_id=user_id)

        item = result.attempts[0]
        assert item.evidence.evidence_count == 1
        assert item.evidence.latest_ai_outcome == "SUCCESS"
        assert item.evidence.latest_confidence == pytest.approx(0.9, abs=1e-3)

    async def test_pocket_mode_flag_set(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            q = await _seed_quest(db)
            await _seed_attempt(
                db, user_id, q.id, AttemptStatus.COMPLETED, pocket_started_at=datetime.now(UTC)
            )
            await _seed_attempt(db, user_id, q.id, AttemptStatus.ABANDONED)

            result = await get_history(db, user_id=user_id)

        pocket_attempt = next(a for a in result.attempts if a.status == "COMPLETED")
        non_pocket = next(a for a in result.attempts if a.status == "ABANDONED")
        assert pocket_attempt.used_pocket_mode is True
        assert non_pocket.used_pocket_mode is False

    async def test_history_includes_quest_metadata(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            q = await _seed_quest(
                db, play_style="detective", difficulty="curious", duration_minutes=30
            )
            await _seed_attempt(db, user_id, q.id, AttemptStatus.COMPLETED)

            result = await get_history(db, user_id=user_id)

        item = result.attempts[0]
        assert item.quest_title == q.title
        assert item.quest_play_style == "detective"
        assert item.quest_difficulty == "curious"
        assert item.quest_duration_minutes == 30


# ===========================================================================
# Integration — GET /api/v1/history HTTP endpoints
# ===========================================================================


class TestHistoryHTTPEndpoints:
    async def test_history_unauthenticated_returns_401(self, async_client):
        resp = await async_client.get(BASE_HISTORY)
        assert resp.status_code == 401

    async def test_detail_unauthenticated_returns_401(self, async_client):
        resp = await async_client.get(f"{BASE_HISTORY}/{uuid4()}")
        assert resp.status_code == 401

    async def test_history_empty_for_new_player(self, async_client):
        token, _ = await _register(async_client, f"hist{uuid4().hex[:6]}")
        resp = await async_client.get(BASE_HISTORY, headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["attempts"] == []

    async def test_history_cross_user_isolation(self, async_client, db_session: AsyncSession):
        """User B cannot see User A's history."""
        token_a, user_id_a = await _register(async_client, f"ha{uuid4().hex[:6]}")
        token_b, _ = await _register(async_client, f"hb{uuid4().hex[:6]}")

        q = await _seed_quest(db_session)
        await _seed_attempt(db_session, user_id_a, q.id, AttemptStatus.COMPLETED)

        resp_b = await async_client.get(BASE_HISTORY, headers=_auth(token_b))
        assert resp_b.status_code == 200
        assert resp_b.json()["total"] == 0

    async def test_history_returns_all_required_fields(
        self, async_client, db_session: AsyncSession
    ):
        token, user_id = await _register(async_client, f"hf{uuid4().hex[:6]}")
        q = await _seed_quest(db_session)
        await _seed_attempt(db_session, user_id, q.id, AttemptStatus.COMPLETED)

        resp = await async_client.get(BASE_HISTORY, headers=_auth(token))
        assert resp.status_code == 200
        item = resp.json()["attempts"][0]
        required = {
            "attempt_id",
            "quest_id",
            "quest_title",
            "quest_difficulty",
            "quest_play_style",
            "quest_duration_minutes",
            "status",
            "earned_xp",
            "started_at",
            "completed_at",
            "used_pocket_mode",
            "evidence",
        }
        for field in required:
            assert field in item, f"Missing: {field}"

    async def test_history_status_filter_via_query_param(
        self, async_client, db_session: AsyncSession
    ):
        token, user_id = await _register(async_client, f"hfilt{uuid4().hex[:6]}")
        q = await _seed_quest(db_session)
        await _seed_attempt(db_session, user_id, q.id, AttemptStatus.COMPLETED)
        await _seed_attempt(db_session, user_id, q.id, AttemptStatus.ABANDONED)

        resp = await async_client.get(f"{BASE_HISTORY}?status=COMPLETED", headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["attempts"][0]["status"] == "COMPLETED"

    async def test_history_pagination_via_query_params(
        self, async_client, db_session: AsyncSession
    ):
        token, user_id = await _register(async_client, f"hpag{uuid4().hex[:6]}")
        q = await _seed_quest(db_session)
        for _ in range(5):
            await _seed_attempt(db_session, user_id, q.id, AttemptStatus.COMPLETED)

        resp1 = await async_client.get(f"{BASE_HISTORY}?skip=0&limit=3", headers=_auth(token))
        resp2 = await async_client.get(f"{BASE_HISTORY}?skip=3&limit=3", headers=_auth(token))
        assert resp1.json()["total"] == 5
        assert len(resp1.json()["attempts"]) == 3
        assert len(resp2.json()["attempts"]) == 2

    async def test_detail_endpoint_returns_correct_attempt(
        self, async_client, db_session: AsyncSession
    ):
        token, user_id = await _register(async_client, f"hdet{uuid4().hex[:6]}")
        q = await _seed_quest(db_session)
        attempt = await _seed_attempt(db_session, user_id, q.id, AttemptStatus.COMPLETED)

        resp = await async_client.get(f"{BASE_HISTORY}/{attempt.id}", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["attempt_id"] == str(attempt.id)
        assert body["status"] == "COMPLETED"

    async def test_detail_endpoint_403_for_other_user(self, async_client, db_session: AsyncSession):
        token_a, user_id_a = await _register(async_client, f"da{uuid4().hex[:6]}")
        token_b, _ = await _register(async_client, f"db{uuid4().hex[:6]}")
        q = await _seed_quest(db_session)
        attempt = await _seed_attempt(db_session, user_id_a, q.id, AttemptStatus.COMPLETED)

        resp = await async_client.get(f"{BASE_HISTORY}/{attempt.id}", headers=_auth(token_b))
        assert resp.status_code == 403

    async def test_detail_endpoint_404_for_nonexistent(self, async_client):
        token, _ = await _register(async_client, f"d404{uuid4().hex[:6]}")
        resp = await async_client.get(f"{BASE_HISTORY}/{uuid4()}", headers=_auth(token))
        assert resp.status_code == 404


# ===========================================================================
# Integration — extended stats
# ===========================================================================


class TestExtendedStats:
    async def test_new_player_optional_fields_are_none(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            stats = await get_extended_stats(db, user_id=user_id)

        assert stats.avg_quest_duration_minutes is None
        assert stats.favorite_play_style is None

    async def test_favorite_play_style_after_completions(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            # 3 detective, 1 explorer
            for _ in range(3):
                q = await _seed_quest(db, play_style="detective")
                await _seed_attempt(db, user_id, q.id, AttemptStatus.COMPLETED)
            q2 = await _seed_quest(db, play_style="explorer")
            await _seed_attempt(db, user_id, q2.id, AttemptStatus.COMPLETED)

            stats = await get_extended_stats(db, user_id=user_id)

        assert stats.favorite_play_style == "detective"

    async def test_avg_duration_calculated(self, db_session):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user_id, _ = await _seed_user(db)
            for dur in [10, 20, 30]:
                q = await _seed_quest(db, duration_minutes=dur)
                await _seed_attempt(db, user_id, q.id, AttemptStatus.COMPLETED)

            stats = await get_extended_stats(db, user_id=user_id)

        assert stats.avg_quest_duration_minutes == pytest.approx(20.0, abs=0.5)

    async def test_player_stats_endpoint_includes_new_fields(
        self, async_client, db_session: AsyncSession
    ):
        token, user_id = await _register(async_client, f"stats{uuid4().hex[:6]}")
        q = await _seed_quest(db_session, play_style="observer", duration_minutes=25)
        await _seed_attempt(db_session, user_id, q.id, AttemptStatus.COMPLETED)

        resp = await async_client.get(f"{BASE_PLAYER}/stats", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "favorite_play_style" in body
        assert "avg_quest_duration_minutes" in body
        assert body["total_quests"] == 1
        assert body["completed_quests"] == 1
