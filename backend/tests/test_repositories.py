import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.achievement import Achievement
from app.models.ai_analysis import AIAnalysis
from app.models.evidence import Evidence
from app.models.player_profile import PlayerProfile
from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt
from app.models.reflection import Reflection
from app.models.user import User
from app.models.xp_transaction import XPTransaction
from app.repositories.evidence_repository import AIAnalysisRepository, EvidenceRepository
from app.repositories.progression_repository import (
    AchievementRepository,
    XPTransactionRepository,
)
from app.repositories.quest_repository import QuestAttemptRepository, QuestRepository
from app.repositories.reflection_repository import ReflectionRepository
from app.repositories.user_repository import PlayerProfileRepository, UserRepository


@pytest.mark.asyncio
async def test_user_and_profile_repository(db_session: AsyncSession):
    user_repo = UserRepository()
    profile_repo = PlayerProfileRepository()

    # Create User
    user = User(
        email="hero@reality.exe",
        username="hero",
        password_hash=hash_password("Secret123!"),
    )
    user = await user_repo.create(db_session, user)
    assert user.id is not None

    # Fetch User by email & username
    by_email = await user_repo.get_by_email(db_session, "hero@reality.exe")
    by_username = await user_repo.get_by_username(db_session, "hero")
    assert by_email is not None and by_email.id == user.id
    assert by_username is not None and by_username.id == user.id

    # Create PlayerProfile
    profile = PlayerProfile(
        user_id=user.id,
        display_name="Cyber Hero",
        level=1,
        total_xp=100,
        preferred_personality="Sarcastic AI",
        preferred_play_style="Explorer",
    )
    profile = await profile_repo.create(db_session, profile)
    assert profile.id is not None

    fetched_profile = await profile_repo.get_by_user_id(db_session, user.id)
    assert fetched_profile is not None
    assert fetched_profile.display_name == "Cyber Hero"


@pytest.mark.asyncio
async def test_quest_and_attempt_repository(db_session: AsyncSession):
    user_repo = UserRepository()
    quest_repo = QuestRepository()
    attempt_repo = QuestAttemptRepository()

    user = await user_repo.create(
        db_session,
        User(
            email="runner@reality.exe",
            username="runner",
            password_hash=hash_password("Pass123!"),
        ),
    )

    quest = Quest(
        title="Find the Old Oak",
        brief="Walk 500m to the nearest park and observe the oldest tree.",
        duration_minutes=15,
        environment="OUTDOORS",
        difficulty="MEDIUM",
        play_style="OBSERVER",
        personality="CALM",
        objectives_json=[{"id": "obj1", "instruction": "Take a photo of the tree"}],
        xp_reward=100,
        evidence_required=True,
        safety_notes="Watch out for muddy terrain.",
        model_name="llama3",
        prompt_version="1.0",
    )
    quest = await quest_repo.create(db_session, quest)
    assert quest.id is not None

    recent_quests = await quest_repo.get_recent_quests(db_session, limit=5)
    assert len(recent_quests) >= 1

    # Create Quest Attempt
    attempt = QuestAttempt(
        quest_id=quest.id,
        user_id=user.id,
        status="ACTIVE",
    )
    attempt = await attempt_repo.create(db_session, attempt)
    assert attempt.id is not None

    active_attempt = await attempt_repo.get_active_attempt(db_session, user.id)
    assert active_attempt is not None
    assert active_attempt.id == attempt.id

    user_attempts = await attempt_repo.get_by_user_id(db_session, user.id)
    assert len(user_attempts) == 1


@pytest.mark.asyncio
async def test_evidence_and_ai_analysis_repository(db_session: AsyncSession):
    user_repo = UserRepository()
    quest_repo = QuestRepository()
    attempt_repo = QuestAttemptRepository()
    evidence_repo = EvidenceRepository()
    analysis_repo = AIAnalysisRepository()

    user = await user_repo.create(
        db_session,
        User(
            email="scout@reality.exe",
            username="scout",
            password_hash=hash_password("Pass123!"),
        ),
    )

    quest = await quest_repo.create(
        db_session,
        Quest(
            title="Urban Exploration",
            brief="Explore the city plaza.",
            duration_minutes=20,
            environment="URBAN",
            difficulty="EASY",
            play_style="EXPLORER",
            personality="CURIOUS",
            objectives_json=[],
            xp_reward=120,
            evidence_required=True,
            model_name="llama3",
            prompt_version="1.0",
        ),
    )

    attempt = await attempt_repo.create(
        db_session, QuestAttempt(quest_id=quest.id, user_id=user.id, status="ACTIVE")
    )

    evidence = Evidence(
        attempt_id=attempt.id,
        storage_key="uploads/evidences/test1.jpg",
        mime_type="image/jpeg",
        size_bytes=102400,
        checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    evidence = await evidence_repo.create(db_session, evidence)
    assert evidence.id is not None

    evidences = await evidence_repo.get_by_attempt_id(db_session, attempt.id)
    assert len(evidences) == 1

    analysis = AIAnalysis(
        evidence_id=evidence.id,
        model_name="llava",
        model_version="1.0",
        confidence=0.95,
        findings_json={"object_detected": "tree", "outdoor_confidence": 0.98},
        completion_recommendation="PASS",
    )
    analysis = await analysis_repo.create(db_session, analysis)
    assert analysis.id is not None

    analyses = await analysis_repo.get_by_evidence_id(db_session, evidence.id)
    assert len(analyses) == 1


@pytest.mark.asyncio
async def test_progression_and_reflection_repositories(db_session: AsyncSession):
    user_repo = UserRepository()
    quest_repo = QuestRepository()
    attempt_repo = QuestAttemptRepository()
    xp_repo = XPTransactionRepository()
    achievement_repo = AchievementRepository()
    reflection_repo = ReflectionRepository()

    user = await user_repo.create(
        db_session,
        User(
            email="achiever@reality.exe",
            username="achiever",
            password_hash=hash_password("Pass123!"),
        ),
    )

    # XP Transaction
    xp_tx = XPTransaction(
        user_id=user.id,
        amount=100,
        reason="Quest Completion",
        reference_id="quest_attempt_1",
    )
    xp_tx = await xp_repo.create(db_session, xp_tx)
    assert xp_tx.id is not None

    txs = await xp_repo.get_by_user_id(db_session, user.id)
    assert len(txs) == 1

    # Achievement
    achievement = Achievement(
        user_id=user.id,
        achievement_key="FIRST_CONTACT",
    )
    achievement = await achievement_repo.create(db_session, achievement)
    assert achievement.id is not None

    achievements = await achievement_repo.get_by_user_id(db_session, user.id)
    assert len(achievements) == 1

    by_key = await achievement_repo.get_by_user_and_key(db_session, user.id, "FIRST_CONTACT")
    assert by_key is not None

    # Reflection
    quest = await quest_repo.create(
        db_session,
        Quest(
            title="Reflection Quest",
            brief="Reflect on your day.",
            duration_minutes=10,
            environment="INDOORS",
            difficulty="EASY",
            play_style="MINDFUL",
            personality="PHILOSOPHICAL",
            objectives_json=[],
            xp_reward=50,
            evidence_required=False,
            model_name="llama3",
            prompt_version="1.0",
        ),
    )
    attempt = await attempt_repo.create(
        db_session, QuestAttempt(quest_id=quest.id, user_id=user.id, status="COMPLETED")
    )

    reflection = Reflection(
        attempt_id=attempt.id,
        text="I observed the birds in the park and felt peaceful.",
        model_name="llama3",
    )
    reflection = await reflection_repo.create(db_session, reflection)
    assert reflection.id is not None

    reflections = await reflection_repo.get_by_attempt_id(db_session, attempt.id)
    assert len(reflections) == 1
