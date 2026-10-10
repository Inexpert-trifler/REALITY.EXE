"""Comprehensive tests for player profile, XP service, and stats endpoints.

Covers:
  Unit tests (no DB):
    - calculate_level at every curve boundary
    - calculate_level with custom curve
    - calculate_level at max level
    - get_progress at every band
    - get_progress at max level

  Integration tests (HTTP + SQLite):
    - GET /player/profile authenticated
    - GET /player/profile unauthenticated → 401
    - PATCH /player/profile valid fields
    - PATCH /player/profile invalid personality → 422
    - PATCH /player/profile invalid play_style → 422
    - PATCH /player/profile blank display_name → 422
    - PATCH /player/profile XP/level fields ignored (not accepted)
    - PATCH /player/profile empty body → returns unchanged profile
    - GET /player/stats authenticated
    - GET /player/stats unauthenticated → 401
    - award_xp increases XP and recalculates level
    - award_xp negative/zero amount → 400
    - award_xp duplicate reference_id → idempotent
    - award_xp triggers level-up
    - stats completion rate calculation
    - stats with zero quests
"""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quest_attempt import QuestAttempt
from app.services import xp_service
from app.services.xp_service import calculate_level, get_progress

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_AUTH = "/api/v1/auth"
BASE_PLAYER = "/api/v1/player"

# The default XP curve used across tests
DEFAULT_CURVE = [0, 100, 250, 500, 850, 1300]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg(username: str, email: str) -> dict:
    return {
        "username": username,
        "email": email,
        "password": "Secure1234",
        "display_name": f"Player {username}",
    }


async def _register_and_token(client: AsyncClient, username: str, email: str) -> str:
    """Register a player and return their access token."""
    resp = await client.post(f"{BASE_AUTH}/register", json=_reg(username, email))
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# Unit tests — pure level / progress calculation (no DB, no HTTP)
# ===========================================================================


class TestCalculateLevel:
    def test_level_1_at_zero_xp(self):
        assert calculate_level(0, DEFAULT_CURVE) == 1

    def test_level_1_just_below_level_2(self):
        assert calculate_level(99, DEFAULT_CURVE) == 1

    def test_level_2_at_threshold(self):
        assert calculate_level(100, DEFAULT_CURVE) == 2

    def test_level_2_mid_band(self):
        assert calculate_level(175, DEFAULT_CURVE) == 2

    def test_level_3_at_threshold(self):
        assert calculate_level(250, DEFAULT_CURVE) == 3

    def test_level_4_at_threshold(self):
        assert calculate_level(500, DEFAULT_CURVE) == 4

    def test_level_5_at_threshold(self):
        assert calculate_level(850, DEFAULT_CURVE) == 5

    def test_level_6_at_threshold(self):
        assert calculate_level(1300, DEFAULT_CURVE) == 6

    def test_level_6_well_above_max_threshold(self):
        """XP beyond the last defined threshold stays at max level."""
        assert calculate_level(99999, DEFAULT_CURVE) == 6

    def test_single_entry_curve(self):
        """A curve with only one entry means everyone is at level 1."""
        assert calculate_level(5000, [0]) == 1

    def test_custom_curve(self):
        custom = [0, 50, 200]
        assert calculate_level(0, custom) == 1
        assert calculate_level(50, custom) == 2
        assert calculate_level(200, custom) == 3
        assert calculate_level(999, custom) == 3

    def test_empty_curve_returns_level_1(self):
        assert calculate_level(500, []) == 1


class TestGetProgress:
    def test_level_1_start(self):
        p = get_progress(0, DEFAULT_CURVE)
        assert p.current_level == 1
        assert p.current_xp == 0
        assert p.xp_for_current_level == 0
        assert p.xp_for_next_level == 100
        assert p.xp_into_level == 0
        assert p.xp_needed_for_next == 100
        assert p.progress_percent == 0.0

    def test_halfway_through_level_1(self):
        p = get_progress(50, DEFAULT_CURVE)
        assert p.current_level == 1
        assert p.xp_into_level == 50
        assert p.xp_needed_for_next == 50
        assert p.progress_percent == 50.0

    def test_exactly_at_level_2(self):
        p = get_progress(100, DEFAULT_CURVE)
        assert p.current_level == 2
        assert p.xp_for_current_level == 100
        assert p.xp_for_next_level == 250
        assert p.xp_into_level == 0
        assert p.xp_needed_for_next == 150
        assert p.progress_percent == 0.0

    def test_max_level_has_no_next(self):
        p = get_progress(1300, DEFAULT_CURVE)
        assert p.current_level == 6
        assert p.xp_for_next_level is None
        assert p.xp_needed_for_next is None
        assert p.progress_percent == 100.0

    def test_beyond_max_level(self):
        p = get_progress(9999, DEFAULT_CURVE)
        assert p.current_level == 6
        assert p.xp_for_next_level is None
        assert p.progress_percent == 100.0

    def test_progress_percent_accuracy(self):
        # Level 2: band is 100→250, width 150.  At 175 XP: 75 into the band.
        p = get_progress(175, DEFAULT_CURVE)
        assert p.current_level == 2
        assert p.xp_into_level == 75
        assert round(p.progress_percent, 2) == 50.0


# ===========================================================================
# Integration tests — HTTP API
# ===========================================================================


class TestGetProfile:
    async def test_get_profile_authenticated(self, async_client: AsyncClient):
        token = await _register_and_token(async_client, "profuser", "prof@example.com")
        resp = await async_client.get(f"{BASE_PLAYER}/profile", headers=_auth(token))
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["display_name"] == "Player profuser"
        assert body["level"] == 1
        assert body["total_xp"] == 0
        assert body["preferred_personality"] is None
        assert body["preferred_play_style"] is None
        assert "id" in body
        assert "user_id" in body

    async def test_get_profile_unauthenticated(self, async_client: AsyncClient):
        resp = await async_client.get(f"{BASE_PLAYER}/profile")
        assert resp.status_code == 401, resp.text
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    async def test_get_profile_invalid_token(self, async_client: AsyncClient):
        resp = await async_client.get(
            f"{BASE_PLAYER}/profile",
            headers={"Authorization": "Bearer garbage.token.here"},
        )
        assert resp.status_code == 401, resp.text


class TestPatchProfile:
    async def test_patch_display_name(self, async_client: AsyncClient):
        token = await _register_and_token(async_client, "patchuser", "patch@example.com")
        resp = await async_client.patch(
            f"{BASE_PLAYER}/profile",
            json={"display_name": "New Name"},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["display_name"] == "New Name"

    async def test_patch_personality(self, async_client: AsyncClient):
        token = await _register_and_token(async_client, "persuser", "pers@example.com")
        resp = await async_client.patch(
            f"{BASE_PLAYER}/profile",
            json={"preferred_personality": "Wizard"},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["preferred_personality"] == "Wizard"

    async def test_patch_play_style(self, async_client: AsyncClient):
        token = await _register_and_token(async_client, "styleuser", "style@example.com")
        resp = await async_client.patch(
            f"{BASE_PLAYER}/profile",
            json={"preferred_play_style": "explorer"},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["preferred_play_style"] == "explorer"

    async def test_patch_invalid_personality_returns_422(self, async_client: AsyncClient):
        token = await _register_and_token(async_client, "badpers", "badpers@example.com")
        resp = await async_client.patch(
            f"{BASE_PLAYER}/profile",
            json={"preferred_personality": "NotAPersonality"},
            headers=_auth(token),
        )
        assert resp.status_code == 422, resp.text

    async def test_patch_invalid_play_style_returns_422(self, async_client: AsyncClient):
        token = await _register_and_token(async_client, "badstyle", "badstyle@example.com")
        resp = await async_client.patch(
            f"{BASE_PLAYER}/profile",
            json={"preferred_play_style": "time_traveller"},
            headers=_auth(token),
        )
        assert resp.status_code == 422, resp.text

    async def test_patch_blank_display_name_returns_422(self, async_client: AsyncClient):
        token = await _register_and_token(async_client, "blankname", "blankname@example.com")
        resp = await async_client.patch(
            f"{BASE_PLAYER}/profile",
            json={"display_name": "   "},
            headers=_auth(token),
        )
        assert resp.status_code == 422, resp.text

    async def test_patch_empty_body_returns_current_profile(self, async_client: AsyncClient):
        """An empty PATCH should return the current profile unchanged."""
        token = await _register_and_token(async_client, "emptyp", "emptyp@example.com")
        resp = await async_client.patch(
            f"{BASE_PLAYER}/profile",
            json={},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["display_name"] == "Player emptyp"

    async def test_patch_xp_field_ignored(self, async_client: AsyncClient):
        """The PATCH endpoint must not accept total_xp — it should be ignored (422 or stripped)."""
        token = await _register_and_token(async_client, "xpignore", "xpignore@example.com")
        resp = await async_client.patch(
            f"{BASE_PLAYER}/profile",
            json={"total_xp": 99999},
            headers=_auth(token),
        )
        # Either 422 (extra field rejected) or 200 with XP unchanged
        if resp.status_code == 200:
            assert resp.json()["total_xp"] == 0, "XP must not be modifiable via PATCH"
        else:
            assert resp.status_code == 422

    async def test_patch_level_field_ignored(self, async_client: AsyncClient):
        """The PATCH endpoint must not accept level."""
        token = await _register_and_token(async_client, "lvlignore", "lvlignore@example.com")
        resp = await async_client.patch(
            f"{BASE_PLAYER}/profile",
            json={"level": 99},
            headers=_auth(token),
        )
        if resp.status_code == 200:
            assert resp.json()["level"] == 1, "Level must not be modifiable via PATCH"
        else:
            assert resp.status_code == 422

    async def test_patch_unauthenticated_returns_401(self, async_client: AsyncClient):
        resp = await async_client.patch(f"{BASE_PLAYER}/profile", json={"display_name": "Hacker"})
        assert resp.status_code == 401, resp.text


# ===========================================================================
# XP service — integration (requires DB session)
# ===========================================================================


class TestAwardXP:
    async def test_award_xp_increases_total(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        token = await _register_and_token(async_client, "xpuser1", "xpuser1@example.com")

        # Get user_id from /me
        me = await async_client.get(f"{BASE_AUTH}/me", headers=_auth(token))
        user_id = UUID(me.json()["id"])

        profile = await xp_service.award_xp(
            db_session, user_id, 50, "test award", reference_id="test-ref-1"
        )
        assert profile.total_xp == 50
        assert profile.level == 1  # still L1 (need 100 for L2)

    async def test_award_xp_triggers_level_up(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        token = await _register_and_token(async_client, "xpuser2", "xpuser2@example.com")
        me = await async_client.get(f"{BASE_AUTH}/me", headers=_auth(token))
        user_id = UUID(me.json()["id"])

        profile = await xp_service.award_xp(
            db_session, user_id, 100, "first quest", reference_id="quest-first"
        )
        assert profile.total_xp == 100
        assert profile.level == 2

    async def test_award_xp_multiple_awards_accumulate(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        token = await _register_and_token(async_client, "xpuser3", "xpuser3@example.com")
        me = await async_client.get(f"{BASE_AUTH}/me", headers=_auth(token))
        user_id = UUID(me.json()["id"])

        await xp_service.award_xp(db_session, user_id, 100, "quest 1", reference_id="q1")
        await xp_service.award_xp(db_session, user_id, 150, "quest 2", reference_id="q2")
        profile = await xp_service.award_xp(db_session, user_id, 250, "quest 3", reference_id="q3")
        assert profile.total_xp == 500
        assert profile.level == 4

    async def test_award_zero_xp_raises_400(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        from app.core.exceptions import BadRequestException

        token = await _register_and_token(async_client, "xpuser4", "xpuser4@example.com")
        me = await async_client.get(f"{BASE_AUTH}/me", headers=_auth(token))
        user_id = UUID(me.json()["id"])

        with pytest.raises(BadRequestException, match="positive"):
            await xp_service.award_xp(db_session, user_id, 0, "bad award")

    async def test_award_negative_xp_raises_400(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        from app.core.exceptions import BadRequestException

        token = await _register_and_token(async_client, "xpuser5", "xpuser5@example.com")
        me = await async_client.get(f"{BASE_AUTH}/me", headers=_auth(token))
        user_id = UUID(me.json()["id"])

        with pytest.raises(BadRequestException, match="positive"):
            await xp_service.award_xp(db_session, user_id, -50, "bad award")

    async def test_duplicate_reference_id_is_idempotent(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Awarding XP with the same reference_id twice must only credit once."""
        token = await _register_and_token(async_client, "xpuser6", "xpuser6@example.com")
        me = await async_client.get(f"{BASE_AUTH}/me", headers=_auth(token))
        user_id = UUID(me.json()["id"])

        ref = "idempotent-ref-abc"
        await xp_service.award_xp(db_session, user_id, 100, "first time", reference_id=ref)
        profile = await xp_service.award_xp(db_session, user_id, 100, "duplicate", reference_id=ref)
        # XP must still be 100, not 200
        assert profile.total_xp == 100

    async def test_award_xp_without_reference_id_always_processes(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Without a reference_id, every call creates a new transaction (no dedup)."""
        token = await _register_and_token(async_client, "xpuser7", "xpuser7@example.com")
        me = await async_client.get(f"{BASE_AUTH}/me", headers=_auth(token))
        user_id = UUID(me.json()["id"])

        await xp_service.award_xp(db_session, user_id, 50, "no-ref")
        profile = await xp_service.award_xp(db_session, user_id, 50, "no-ref")
        assert profile.total_xp == 100

    async def test_award_xp_unknown_user_raises_400(self, db_session: AsyncSession):
        from app.core.exceptions import BadRequestException

        with pytest.raises(BadRequestException, match="not found"):
            await xp_service.award_xp(db_session, uuid4(), 100, "ghost user")


# ===========================================================================
# Stats endpoint
# ===========================================================================


class TestGetStats:
    async def test_stats_for_new_player(self, async_client: AsyncClient):
        token = await _register_and_token(async_client, "statsuser1", "stats1@example.com")
        resp = await async_client.get(f"{BASE_PLAYER}/stats", headers=_auth(token))
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["level"] == 1
        assert body["total_xp"] == 0
        assert body["total_quests"] == 0
        assert body["completed_quests"] == 0
        assert body["abandoned_quests"] == 0
        assert body["completion_rate"] == 0.0
        assert body["achievements_count"] == 0

        # Level progress checks
        lp = body["level_progress"]
        assert lp["current_level"] == 1
        assert lp["current_xp"] == 0
        assert lp["xp_for_next_level"] == 100
        assert lp["progress_percent"] == 0.0

    async def test_stats_unauthenticated_returns_401(self, async_client: AsyncClient):
        resp = await async_client.get(f"{BASE_PLAYER}/stats")
        assert resp.status_code == 401, resp.text

    async def test_stats_completion_rate_with_attempts(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Seed quest attempts directly and verify stats calculations."""
        from app.models.quest import Quest

        token = await _register_and_token(async_client, "statsuser2", "stats2@example.com")
        me = await async_client.get(f"{BASE_AUTH}/me", headers=_auth(token))
        user_id = UUID(me.json()["id"])

        # Create a minimal quest to satisfy FK constraints
        quest = Quest(
            title="Test Quest",
            brief="Go outside",
            duration_minutes=20,
            environment="park",
            difficulty="chill",
            play_style="explorer",
            personality="Wizard",
            objectives_json="[]",
            xp_reward=100,
            safety_notes="",
            model_name="test",
            prompt_version="v1",
        )
        db_session.add(quest)
        await db_session.flush()
        await db_session.refresh(quest)

        # 3 COMPLETED, 1 ABANDONED
        for status in ["COMPLETED", "COMPLETED", "COMPLETED", "ABANDONED"]:
            attempt = QuestAttempt(
                quest_id=quest.id,
                user_id=user_id,
                status=status,
            )
            db_session.add(attempt)
        await db_session.flush()

        resp = await async_client.get(f"{BASE_PLAYER}/stats", headers=_auth(token))
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["total_quests"] == 4
        assert body["completed_quests"] == 3
        assert body["abandoned_quests"] == 1
        assert body["completion_rate"] == pytest.approx(0.75, abs=1e-4)

    async def test_stats_reflects_xp_award(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """After awarding XP, stats should reflect updated level and XP."""
        token = await _register_and_token(async_client, "statsuser3", "stats3@example.com")
        me = await async_client.get(f"{BASE_AUTH}/me", headers=_auth(token))
        user_id = UUID(me.json()["id"])

        await xp_service.award_xp(db_session, user_id, 250, "big win", reference_id="bw-1")

        resp = await async_client.get(f"{BASE_PLAYER}/stats", headers=_auth(token))
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["total_xp"] == 250
        assert body["level"] == 3
        assert body["level_progress"]["current_level"] == 3
        assert body["level_progress"]["xp_for_current_level"] == 250
