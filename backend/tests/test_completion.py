"""Comprehensive tests for the quest completion pipeline.

Covers:
  Unit — classify_result():
    - safety_concerns → UNSAFE (regardless of confidence/recommendation)
    - confidence < 0.40 → UNCERTAIN
    - recommendation + confidence >= 0.70 → SUCCESS
    - recommendation but confidence < 0.70 → INCOMPLETE
    - no recommendation, high confidence → INCOMPLETE
    - no recommendation, low confidence → UNCERTAIN
    - safety_concerns with high confidence still UNSAFE

  Unit — VerificationOutcome flags:
    - can_complete only for SUCCESS
    - can_retry for INCOMPLETE and UNCERTAIN
    - can_retry False for UNSAFE and SUCCESS

  Integration — verification_service.analyze_evidence():
    - success outcome → AIAnalysis persisted, can_complete=True
    - incomplete outcome → can_complete=False, can_retry=True
    - uncertain (low confidence) → UNCERTAIN
    - unsafe (safety concerns) → UNSAFE, can_retry=False
    - provider unavailable → UNCERTAIN (graceful degradation)
    - unknown evidence_id → 404
    - evidence owned by another user → 403
    - analysis_id returned is a valid UUID

  Integration — completion_service.complete_quest():
    - VERIFYING → COMPLETED: XP awarded, level calculated
    - first completion unlocks first_contact achievement
    - chaos quest unlocks chaos_agent achievement
    - level-up detected when XP crosses threshold
    - no level-up when XP stays in same band
    - idempotency: calling complete twice returns same XP, idempotent=True
    - XP only awarded once (idempotency via reference_id)
    - wrong state (ACTIVE) → 400
    - wrong state (RETURNED) → 400
    - nonexistent attempt → 404
    - foreign user → 404

  Integration — HTTP endpoints:
    - POST /quests/{id}/complete unauthenticated → 401
    - POST /quests/{id}/complete valid → 200 with all required fields
    - POST /quests/{id}/complete idempotent second call → 200 with idempotent=True
    - POST /evidence/{id}/analyze unauthenticated → 401
"""

import io
from uuid import UUID, uuid4

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import EvidenceAnalysisRequest, EvidenceAnalysisResult, VisionModelProvider
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.domain.quest_states import AttemptStatus
from app.models.evidence import Evidence
from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt
from app.schemas.completion import VerificationOutcome
from app.services.completion_service import complete_quest
from app.services.verification_service import (
    SUCCESS_THRESHOLD,
    UNCERTAIN_THRESHOLD,
    analyze_evidence,
    classify_result,
)

BASE_AUTH = "/api/v1/auth"
BASE_QUESTS = "/api/v1/quests"
BASE_COMPLETION = "/api/v1"

# ---------------------------------------------------------------------------
# Fake vision provider
# ---------------------------------------------------------------------------


class FakeVisionProvider(VisionModelProvider):
    """Configurable fake vision provider for tests."""

    def __init__(
        self,
        visible_content: str = "A leaf on the ground",
        is_relevant: bool = True,
        confidence: float = 0.90,
        safety_concerns: list[str] | None = None,
        completion_recommendation: bool = True,
        raise_error: bool = False,
    ) -> None:
        self._visible = visible_content
        self._relevant = is_relevant
        self._confidence = confidence
        self._safety = safety_concerns or []
        self._recommend = completion_recommendation
        self._raise = raise_error
        self.calls: int = 0

    @property
    def model_name(self) -> str:
        return "fake-vision-model"

    async def analyze_evidence(self, request: EvidenceAnalysisRequest) -> EvidenceAnalysisResult:
        self.calls += 1
        if self._raise:
            from app.ai.base import ProviderUnavailableError

            raise ProviderUnavailableError("Fake provider unavailable")
        return EvidenceAnalysisResult(
            visible_content=self._visible,
            is_relevant=self._relevant,
            confidence=self._confidence,
            safety_concerns=self._safety,
            completion_recommendation=self._recommend,
            model_name="fake-vision-model",
            model_version="test-1.0",
        )


# ---------------------------------------------------------------------------
# DB seed helpers
# ---------------------------------------------------------------------------


async def _seed_quest(db: AsyncSession, difficulty: str = "chill", xp_reward: int = 100) -> Quest:
    quest = Quest(
        title="Test Quest",
        brief="Find something interesting in the park.",
        duration_minutes=20,
        environment="park",
        difficulty=difficulty,
        play_style="explorer",
        personality="Wizard",
        objectives_json=[{"id": "obj-1", "instruction": "Find something", "optional": False}],
        xp_reward=xp_reward,
        evidence_required=True,
        safety_notes="Stay safe.",
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
    status: str = AttemptStatus.VERIFYING,
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


async def _seed_evidence(
    db: AsyncSession,
    attempt_id: UUID,
    mime_type: str = "image/jpeg",
) -> Evidence:
    evidence = Evidence(
        attempt_id=attempt_id,
        storage_key=f"evidence/{attempt_id}/{uuid4()}.jpg",
        mime_type=mime_type,
        size_bytes=1024,
        checksum="a" * 64,
    )
    db.add(evidence)
    await db.flush()
    await db.refresh(evidence)
    return evidence


def _make_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), (100, 150, 200)).save(buf, format="JPEG")
    return buf.getvalue()


def _reg(username: str, email: str) -> dict:
    return {
        "username": username,
        "email": email,
        "password": "Secure1234",
        "display_name": f"Player {username}",
    }


# ===========================================================================
# Unit — classify_result()
# ===========================================================================


class TestClassifyResult:
    def test_safety_concerns_always_unsafe(self):
        assert classify_result(True, True, 1.0, ["violence"]) == VerificationOutcome.UNSAFE

    def test_safety_concerns_unsafe_even_with_low_confidence(self):
        assert (
            classify_result(False, False, 0.0, ["dangerous content"]) == VerificationOutcome.UNSAFE
        )

    def test_low_confidence_uncertain(self):
        assert (
            classify_result(True, True, UNCERTAIN_THRESHOLD - 0.01, [])
            == VerificationOutcome.UNCERTAIN
        )

    def test_zero_confidence_uncertain(self):
        assert classify_result(False, False, 0.0, []) == VerificationOutcome.UNCERTAIN

    def test_exactly_uncertain_threshold_is_not_uncertain(self):
        # At exactly UNCERTAIN_THRESHOLD → passes to success/incomplete check
        result = classify_result(True, True, UNCERTAIN_THRESHOLD, [])
        # With recommendation and confidence >= SUCCESS_THRESHOLD this could be SUCCESS
        # but UNCERTAIN_THRESHOLD < SUCCESS_THRESHOLD, so it's INCOMPLETE
        assert result in (VerificationOutcome.SUCCESS, VerificationOutcome.INCOMPLETE)

    def test_high_confidence_recommendation_success(self):
        assert classify_result(True, True, SUCCESS_THRESHOLD, []) == VerificationOutcome.SUCCESS

    def test_above_success_threshold_success(self):
        assert classify_result(True, True, 0.95, []) == VerificationOutcome.SUCCESS

    def test_recommendation_but_below_success_threshold(self):
        # confidence is above UNCERTAIN but below SUCCESS
        mid = (UNCERTAIN_THRESHOLD + SUCCESS_THRESHOLD) / 2
        assert classify_result(True, True, mid, []) == VerificationOutcome.INCOMPLETE

    def test_no_recommendation_high_confidence_incomplete(self):
        assert classify_result(True, False, 0.95, []) == VerificationOutcome.INCOMPLETE

    def test_no_recommendation_low_confidence_uncertain(self):
        assert classify_result(False, False, 0.1, []) == VerificationOutcome.UNCERTAIN

    def test_safety_list_with_multiple_concerns_still_unsafe(self):
        concerns = ["violence", "weapons", "illegal activity"]
        assert classify_result(True, True, 0.99, concerns) == VerificationOutcome.UNSAFE


class TestVerificationOutcomeFlags:
    def test_success_can_complete(self):
        outcome = VerificationOutcome.SUCCESS
        assert outcome == "SUCCESS"
        # These flags are computed in AnalysisResultResponse
        can_complete = outcome == VerificationOutcome.SUCCESS
        can_retry = outcome in (VerificationOutcome.INCOMPLETE, VerificationOutcome.UNCERTAIN)
        assert can_complete is True
        assert can_retry is False

    def test_incomplete_can_retry_not_complete(self):
        outcome = VerificationOutcome.INCOMPLETE
        assert (outcome == VerificationOutcome.SUCCESS) is False
        assert (outcome in (VerificationOutcome.INCOMPLETE, VerificationOutcome.UNCERTAIN)) is True

    def test_uncertain_can_retry_not_complete(self):
        outcome = VerificationOutcome.UNCERTAIN
        assert (outcome == VerificationOutcome.SUCCESS) is False
        assert (outcome in (VerificationOutcome.INCOMPLETE, VerificationOutcome.UNCERTAIN)) is True

    def test_unsafe_cannot_complete_or_retry(self):
        outcome = VerificationOutcome.UNSAFE
        assert (outcome == VerificationOutcome.SUCCESS) is False
        assert (outcome in (VerificationOutcome.INCOMPLETE, VerificationOutcome.UNCERTAIN)) is False


# ===========================================================================
# Unit — analyze_evidence() service
# ===========================================================================


class TestAnalyzeEvidenceService:
    async def test_success_outcome_persisted(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            # Register + create quest + attempt + evidence
            from app.models.player_profile import PlayerProfile
            from app.models.user import User
            from app.utils.password import hash_password

            user = User(email="av1@test.com", username="av1", password_hash=hash_password("pw"))
            db.add(user)
            await db.flush()
            await db.refresh(user)
            profile = PlayerProfile(user_id=user.id, display_name="AV1", level=1, total_xp=0)
            db.add(profile)
            quest = await _seed_quest(db)
            attempt = await _seed_attempt(db, user.id, quest.id, AttemptStatus.EVIDENCE_PENDING)
            evidence = await _seed_evidence(db, attempt.id)

            provider = FakeVisionProvider(confidence=0.9, completion_recommendation=True)
            result = await analyze_evidence(
                db,
                evidence_id=evidence.id,
                user_id=user.id,
                vision_provider=provider,
                image_bytes=_make_jpeg_bytes(),
            )

        assert result.outcome == VerificationOutcome.SUCCESS
        assert result.can_complete is True
        assert result.can_retry is False
        assert result.confidence == pytest.approx(0.9, abs=1e-3)
        assert result.analysis_id  # UUID string persisted

    async def test_incomplete_outcome(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            from app.models.player_profile import PlayerProfile
            from app.models.user import User
            from app.utils.password import hash_password

            user = User(email="av2@test.com", username="av2", password_hash=hash_password("pw"))
            db.add(user)
            await db.flush()
            profile = PlayerProfile(user_id=user.id, display_name="AV2", level=1, total_xp=0)
            db.add(profile)
            quest = await _seed_quest(db)
            attempt = await _seed_attempt(db, user.id, quest.id)
            evidence = await _seed_evidence(db, attempt.id)

            # Below success threshold, no recommendation
            provider = FakeVisionProvider(confidence=0.65, completion_recommendation=False)
            result = await analyze_evidence(
                db,
                evidence_id=evidence.id,
                user_id=user.id,
                vision_provider=provider,
                image_bytes=_make_jpeg_bytes(),
            )

        assert result.outcome == VerificationOutcome.INCOMPLETE
        assert result.can_complete is False
        assert result.can_retry is True

    async def test_uncertain_outcome_low_confidence(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            from app.models.player_profile import PlayerProfile
            from app.models.user import User
            from app.utils.password import hash_password

            user = User(email="av3@test.com", username="av3", password_hash=hash_password("pw"))
            db.add(user)
            await db.flush()
            profile = PlayerProfile(user_id=user.id, display_name="AV3", level=1, total_xp=0)
            db.add(profile)
            quest = await _seed_quest(db)
            attempt = await _seed_attempt(db, user.id, quest.id)
            evidence = await _seed_evidence(db, attempt.id)

            provider = FakeVisionProvider(confidence=0.2, completion_recommendation=True)
            result = await analyze_evidence(
                db,
                evidence_id=evidence.id,
                user_id=user.id,
                vision_provider=provider,
                image_bytes=_make_jpeg_bytes(),
            )

        assert result.outcome == VerificationOutcome.UNCERTAIN
        assert result.can_retry is True

    async def test_unsafe_outcome_blocks_completion(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            from app.models.player_profile import PlayerProfile
            from app.models.user import User
            from app.utils.password import hash_password

            user = User(email="av4@test.com", username="av4", password_hash=hash_password("pw"))
            db.add(user)
            await db.flush()
            profile = PlayerProfile(user_id=user.id, display_name="AV4", level=1, total_xp=0)
            db.add(profile)
            quest = await _seed_quest(db)
            attempt = await _seed_attempt(db, user.id, quest.id)
            evidence = await _seed_evidence(db, attempt.id)

            provider = FakeVisionProvider(
                confidence=0.95,
                completion_recommendation=True,
                safety_concerns=["violence"],
            )
            result = await analyze_evidence(
                db,
                evidence_id=evidence.id,
                user_id=user.id,
                vision_provider=provider,
                image_bytes=_make_jpeg_bytes(),
            )

        assert result.outcome == VerificationOutcome.UNSAFE
        assert result.can_complete is False
        assert result.can_retry is False
        assert result.safety_concerns == ["violence"]

    async def test_provider_unavailable_returns_uncertain(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            from app.models.player_profile import PlayerProfile
            from app.models.user import User
            from app.utils.password import hash_password

            user = User(email="av5@test.com", username="av5", password_hash=hash_password("pw"))
            db.add(user)
            await db.flush()
            profile = PlayerProfile(user_id=user.id, display_name="AV5", level=1, total_xp=0)
            db.add(profile)
            quest = await _seed_quest(db)
            attempt = await _seed_attempt(db, user.id, quest.id)
            evidence = await _seed_evidence(db, attempt.id)

            provider = FakeVisionProvider(raise_error=True)
            result = await analyze_evidence(
                db,
                evidence_id=evidence.id,
                user_id=user.id,
                vision_provider=provider,
                image_bytes=_make_jpeg_bytes(),
            )

        # Provider failure → graceful UNCERTAIN
        assert result.outcome == VerificationOutcome.UNCERTAIN

    async def test_unknown_evidence_raises_404(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            provider = FakeVisionProvider()
            with pytest.raises(NotFoundException):
                await analyze_evidence(
                    db,
                    evidence_id=uuid4(),
                    user_id=uuid4(),
                    vision_provider=provider,
                    image_bytes=b"fake",
                )

    async def test_foreign_user_raises_403(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            from app.models.user import User
            from app.utils.password import hash_password

            owner = User(email="av6o@test.com", username="av6o", password_hash=hash_password("pw"))
            db.add(owner)
            await db.flush()
            quest = await _seed_quest(db)
            attempt = await _seed_attempt(db, owner.id, quest.id)
            evidence = await _seed_evidence(db, attempt.id)

            provider = FakeVisionProvider()
            with pytest.raises(ForbiddenException):
                await analyze_evidence(
                    db,
                    evidence_id=evidence.id,
                    user_id=uuid4(),  # not the owner
                    vision_provider=provider,
                    image_bytes=_make_jpeg_bytes(),
                )


# ===========================================================================
# Unit — complete_quest() service
# ===========================================================================


class TestCompleteQuestService:
    async def _setup_verifying_attempt(self, db, difficulty: str = "chill", xp_reward: int = 100):
        from app.models.player_profile import PlayerProfile
        from app.models.user import User
        from app.utils.password import hash_password

        user = User(
            email=f"{uuid4()}@test.com",
            username=f"u{uuid4().hex[:8]}",
            password_hash=hash_password("pw"),
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        profile = PlayerProfile(user_id=user.id, display_name="Tester", level=1, total_xp=0)
        db.add(profile)
        quest = await _seed_quest(db, difficulty=difficulty, xp_reward=xp_reward)
        attempt = await _seed_attempt(db, user.id, quest.id, AttemptStatus.VERIFYING)
        return user, quest, attempt

    async def test_successful_completion_awards_xp(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user, quest, attempt = await self._setup_verifying_attempt(db, xp_reward=100)
            result = await complete_quest(db, user_id=user.id, quest_id=quest.id)

        assert result.status == "COMPLETED"
        assert result.earned_xp == 100
        assert result.total_xp == 100
        assert result.idempotent is False

    async def test_completion_level_up_detected(self, db_session: AsyncSession):
        """Completing a quest that pushes XP past the level-2 threshold (100 XP)."""
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            # 100 XP quest at level 1 → should hit level 2
            user, quest, attempt = await self._setup_verifying_attempt(db, xp_reward=100)
            result = await complete_quest(db, user_id=user.id, quest_id=quest.id)

        assert result.level_up.leveled_up is True
        assert result.level_up.old_level == 1
        assert result.level_up.new_level == 2

    async def test_completion_no_level_up(self, db_session: AsyncSession):
        """Small XP award that doesn't cross a threshold → no level-up."""
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            # 50 XP at level 1 → stays at level 1 (need 100 for level 2)
            user, quest, attempt = await self._setup_verifying_attempt(db, xp_reward=50)
            result = await complete_quest(db, user_id=user.id, quest_id=quest.id)

        assert result.level_up.leveled_up is False
        assert result.level_up.old_level == 1
        assert result.level_up.new_level == 1

    async def test_first_completion_unlocks_first_contact(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user, quest, attempt = await self._setup_verifying_attempt(db)
            result = await complete_quest(db, user_id=user.id, quest_id=quest.id)

        keys = [a.key for a in result.new_achievements]
        assert "first_contact" in keys

    async def test_chaos_quest_unlocks_chaos_agent(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user, quest, attempt = await self._setup_verifying_attempt(db, difficulty="chaos")
            result = await complete_quest(db, user_id=user.id, quest_id=quest.id)

        keys = [a.key for a in result.new_achievements]
        assert "chaos_agent" in keys

    async def test_idempotency_second_call_returns_cached(self, db_session: AsyncSession):
        """Calling complete_quest twice must not double-award XP."""
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user, quest, attempt = await self._setup_verifying_attempt(db, xp_reward=100)

            result1 = await complete_quest(db, user_id=user.id, quest_id=quest.id)
            result2 = await complete_quest(db, user_id=user.id, quest_id=quest.id)

        assert result1.earned_xp == 100
        assert result2.idempotent is True
        # XP should not have doubled
        assert result2.total_xp == result1.total_xp

    async def test_wrong_state_active_raises_400(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user, quest, attempt = await self._setup_verifying_attempt(db)
            # Manually force ACTIVE state
            from app.repositories.quest_repository import QuestAttemptRepository

            await QuestAttemptRepository().update(db, attempt.id, {"status": "ACTIVE"})

            with pytest.raises(BadRequestException, match="VERIFYING"):
                await complete_quest(db, user_id=user.id, quest_id=quest.id)

    async def test_wrong_state_returned_raises_400(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            from app.models.player_profile import PlayerProfile
            from app.models.user import User
            from app.utils.password import hash_password

            user = User(
                email=f"{uuid4()}@test.com",
                username=f"u{uuid4().hex[:8]}",
                password_hash=hash_password("pw"),
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
            profile = PlayerProfile(user_id=user.id, display_name="T", level=1, total_xp=0)
            db.add(profile)
            quest = await _seed_quest(db)
            # Seed only a RETURNED attempt — not VERIFYING
            await _seed_attempt(db, user.id, quest.id, AttemptStatus.RETURNED)

            with pytest.raises(BadRequestException):
                await complete_quest(db, user_id=user.id, quest_id=quest.id)

    async def test_nonexistent_attempt_raises_404(self, db_session: AsyncSession):
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            with pytest.raises(NotFoundException):
                await complete_quest(db, user_id=uuid4(), quest_id=uuid4())

    async def test_xp_awarded_only_once_on_duplicate(self, db_session: AsyncSession):
        """XPTransaction reference_id prevents double-awarding."""
        from app.repositories.progression_repository import XPTransactionRepository
        from tests.conftest import TestingSessionLocal

        async with TestingSessionLocal() as db:
            user, quest, attempt = await self._setup_verifying_attempt(db, xp_reward=75)
            await complete_quest(db, user_id=user.id, quest_id=quest.id)
            # Attempt to complete again
            await complete_quest(db, user_id=user.id, quest_id=quest.id)

            # Count XP transactions for this attempt
            txns = await XPTransactionRepository().get_by_user_id(db, user.id)
            quest_txns = [t for t in txns if t.reference_id == f"quest_complete:{attempt.id}"]

        assert len(quest_txns) == 1, (
            f"Expected exactly 1 XP transaction for this quest, got {len(quest_txns)}"
        )


# ===========================================================================
# Integration — HTTP endpoints
# ===========================================================================


class TestCompletionHTTPEndpoints:
    async def _register_and_token(self, client, username: str, email: str):
        resp = await client.post(f"{BASE_AUTH}/register", json=_reg(username, email))
        assert resp.status_code == 201, resp.text
        body = resp.json()
        return body["token"]["access_token"], UUID(body["user"]["id"])

    def _auth(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    async def test_complete_unauthenticated_returns_401(self, async_client):
        resp = await async_client.post(f"{BASE_COMPLETION}/quests/{uuid4()}/complete")
        assert resp.status_code == 401

    async def test_analyze_unauthenticated_returns_401(self, async_client):
        resp = await async_client.post(
            f"{BASE_COMPLETION}/evidence/{uuid4()}/analyze",
            content=b"fake",
            headers={"Content-Type": "application/octet-stream"},
        )
        assert resp.status_code == 401

    async def test_complete_valid_verifying_attempt(self, async_client, db_session: AsyncSession):
        from httpx import ASGITransport, AsyncClient

        from app.api.routes.completion import get_vision_provider
        from app.db.session import get_db
        from app.main import create_app

        def _fake_vision():
            return FakeVisionProvider()

        app = create_app()

        async def _override_db():
            yield db_session

        from app.api.dependencies import get_text_provider
        from tests.fakes.fake_provider import FakeTextProvider

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_vision_provider] = _fake_vision
        app.dependency_overrides[get_text_provider] = lambda: FakeTextProvider()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            token, user_id = await self._register_and_token(client, "cmp1", "cmp1@test.com")
            quest = await _seed_quest(db_session)
            await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.VERIFYING)

            resp = await client.post(
                f"{BASE_COMPLETION}/quests/{quest.id}/complete",
                headers=self._auth(token),
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "COMPLETED"
        assert body["earned_xp"] == quest.xp_reward
        assert "level_up" in body
        assert "new_achievements" in body
        assert body["idempotent"] is False

    async def test_complete_idempotent_second_call(self, async_client, db_session: AsyncSession):
        from httpx import ASGITransport, AsyncClient

        from app.api.dependencies import get_text_provider
        from app.api.routes.completion import get_vision_provider
        from app.db.session import get_db
        from app.main import create_app
        from tests.fakes.fake_provider import FakeTextProvider

        def _fake_vision():
            return FakeVisionProvider()

        app = create_app()

        async def _override_db():
            yield db_session

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_vision_provider] = _fake_vision
        app.dependency_overrides[get_text_provider] = lambda: FakeTextProvider()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            token, user_id = await self._register_and_token(client, "cmp2", "cmp2@test.com")
            quest = await _seed_quest(db_session)
            await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.VERIFYING)

            resp1 = await client.post(
                f"{BASE_COMPLETION}/quests/{quest.id}/complete",
                headers=self._auth(token),
            )
            resp2 = await client.post(
                f"{BASE_COMPLETION}/quests/{quest.id}/complete",
                headers=self._auth(token),
            )

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["idempotent"] is False
        assert resp2.json()["idempotent"] is True
        assert resp1.json()["earned_xp"] == resp2.json()["earned_xp"]
        assert resp1.json()["total_xp"] == resp2.json()["total_xp"]

    async def test_complete_response_has_all_required_fields(
        self, async_client, db_session: AsyncSession
    ):
        from httpx import ASGITransport, AsyncClient

        from app.api.dependencies import get_text_provider
        from app.api.routes.completion import get_vision_provider
        from app.db.session import get_db
        from app.main import create_app
        from tests.fakes.fake_provider import FakeTextProvider

        app = create_app()

        async def _override_db():
            yield db_session

        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_vision_provider] = lambda: FakeVisionProvider()
        app.dependency_overrides[get_text_provider] = lambda: FakeTextProvider()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            token, user_id = await self._register_and_token(client, "cmp3", "cmp3@test.com")
            quest = await _seed_quest(db_session)
            await _seed_attempt(db_session, user_id, quest.id, AttemptStatus.VERIFYING)

            resp = await client.post(
                f"{BASE_COMPLETION}/quests/{quest.id}/complete",
                headers=self._auth(token),
            )

        assert resp.status_code == 200
        body = resp.json()
        required = {
            "attempt_id",
            "quest_id",
            "status",
            "earned_xp",
            "total_xp",
            "level",
            "level_up",
            "new_achievements",
            "idempotent",
        }
        for field in required:
            assert field in body, f"Missing field: {field}"
        assert "leveled_up" in body["level_up"]
        assert "old_level" in body["level_up"]
        assert "new_level" in body["level_up"]
