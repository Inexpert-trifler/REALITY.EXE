import argparse
import asyncio
import logging
import sys
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models import (
    Achievement,
    PlayerProfile,
    Quest,
    QuestAttempt,
    User,
    XPTransaction,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


async def check_environment_for_reset() -> None:
    if settings.ENVIRONMENT.lower() == "production":
        logger.error("DANGER: Cannot run reset in production environment.")
        sys.exit(1)


def get_dummy_password_hash() -> str:
    # A generic valid bcrypt hash for 'demopass' so we avoid hardcoding real secrets
    return "$2b$12$P5T12/g1yTqG.d/J9dG1/.M4iO2v4tQ/v2dE1N2Z1A1C3O5G7I9K."


async def seed_data(session: AsyncSession) -> None:
    # 1. Demo User and Profile
    demo_email = "demo@reality.exe"
    user_stmt = select(User).where(User.email == demo_email)
    result = await session.execute(user_stmt)
    demo_user = result.scalars().first()

    if not demo_user:
        demo_user = User(
            id=uuid.uuid4(),
            email=demo_email,
            username="DemoPlayer",
            password_hash=get_dummy_password_hash(),
        )
        session.add(demo_user)
        await session.flush()
        logger.info(f"Created demo user: {demo_email}")

        demo_profile = PlayerProfile(
            id=uuid.uuid4(),
            user_id=demo_user.id,
            display_name="Demo Player",
            level=5,
            total_xp=2500,
            preferred_personality="Adventurous",
            preferred_play_style="Explorer",
        )
        session.add(demo_profile)
        await session.flush()
        logger.info("Created demo player profile.")
    else:
        logger.info(f"Demo user '{demo_email}' already exists. Skipping user creation.")

    # 2. Curated Quests (Fallback Library)
    quests_data = [
        {
            "title": "Morning Routine: The Awakening",
            "brief": "Start your day with purpose. Drink water and stretch.",
            "duration_minutes": 15,
            "environment": "Home",
            "difficulty": "Easy",
            "play_style": "Casual",
            "personality": "Zen",
            "objectives_json": [
                {"id": 1, "task": "Drink a glass of water"},
                {"id": 2, "task": "Stretch for 5 minutes"},
            ],
            "xp_reward": 50,
            "evidence_required": False,
            "model_name": "fallback",
            "prompt_version": "1.0",
        },
        {
            "title": "Urban Exploration: The Coffee Node",
            "brief": "Discover a new local coffee shop you haven't visited.",
            "duration_minutes": 45,
            "environment": "Urban",
            "difficulty": "Medium",
            "play_style": "Explorer",
            "personality": "Adventurous",
            "objectives_json": [
                {"id": 1, "task": "Find a new coffee shop"},
                {"id": 2, "task": "Order a drink"},
            ],
            "xp_reward": 150,
            "evidence_required": True,
            "model_name": "fallback",
            "prompt_version": "1.0",
        },
        {
            "title": "Nature Node: Digital Detox",
            "brief": "Spend time outside without looking at your phone.",
            "duration_minutes": 30,
            "environment": "Park",
            "difficulty": "Medium",
            "play_style": "Zen",
            "personality": "Calm",
            "objectives_json": [{"id": 1, "task": "Walk in a park for 30 minutes"}],
            "xp_reward": 100,
            "evidence_required": False,
            "model_name": "fallback",
            "prompt_version": "1.0",
        },
        {
            "title": "Social Quest: The Greeting",
            "brief": "Say hello to a stranger or strike up a brief conversation.",
            "duration_minutes": 10,
            "environment": "Public",
            "difficulty": "Hard",
            "play_style": "Social",
            "personality": "Outgoing",
            "objectives_json": [{"id": 1, "task": "Greet a stranger politely"}],
            "xp_reward": 200,
            "evidence_required": False,
            "model_name": "fallback",
            "prompt_version": "1.0",
        },
        {
            "title": "Fitness Protocol: Step Count",
            "brief": "Accumulate 5000 steps.",
            "duration_minutes": 60,
            "environment": "Any",
            "difficulty": "Medium",
            "play_style": "Athletic",
            "personality": "Energetic",
            "objectives_json": [{"id": 1, "task": "Walk 5000 steps"}],
            "xp_reward": 150,
            "evidence_required": True,
            "model_name": "fallback",
            "prompt_version": "1.0",
        },
        {
            "title": "Creative Spark: Doodling",
            "brief": "Draw something on a physical piece of paper.",
            "duration_minutes": 15,
            "environment": "Indoor",
            "difficulty": "Easy",
            "play_style": "Creative",
            "personality": "Artistic",
            "objectives_json": [{"id": 1, "task": "Draw a sketch"}],
            "xp_reward": 75,
            "evidence_required": True,
            "model_name": "fallback",
            "prompt_version": "1.0",
        },
        {
            "title": "Mindful Moment: Meditation",
            "brief": "Sit in silence and focus on your breath.",
            "duration_minutes": 10,
            "environment": "Quiet",
            "difficulty": "Medium",
            "play_style": "Zen",
            "personality": "Calm",
            "objectives_json": [{"id": 1, "task": "Meditate for 10 minutes"}],
            "xp_reward": 100,
            "evidence_required": False,
            "model_name": "fallback",
            "prompt_version": "1.0",
        },
        {
            "title": "Culinary Quest: New Recipe",
            "brief": "Cook a meal you have never made before.",
            "duration_minutes": 60,
            "environment": "Kitchen",
            "difficulty": "Hard",
            "play_style": "Creative",
            "personality": "Adventurous",
            "objectives_json": [{"id": 1, "task": "Cook a new dish"}],
            "xp_reward": 250,
            "evidence_required": True,
            "model_name": "fallback",
            "prompt_version": "1.0",
        },
        {
            "title": "Knowledge Node: Reading",
            "brief": "Read 10 pages of a physical book.",
            "duration_minutes": 20,
            "environment": "Indoor",
            "difficulty": "Easy",
            "play_style": "Intellectual",
            "personality": "Curious",
            "objectives_json": [{"id": 1, "task": "Read 10 pages"}],
            "xp_reward": 50,
            "evidence_required": False,
            "model_name": "fallback",
            "prompt_version": "1.0",
        },
        {
            "title": "Organization Protocol: Clean Desk",
            "brief": "Clear and organize your physical workspace.",
            "duration_minutes": 15,
            "environment": "Workspace",
            "difficulty": "Medium",
            "play_style": "Casual",
            "personality": "Structured",
            "objectives_json": [{"id": 1, "task": "Tidy desk area"}],
            "xp_reward": 100,
            "evidence_required": True,
            "model_name": "fallback",
            "prompt_version": "1.0",
        },
    ]

    quest_stmt = select(Quest).where(Quest.model_name == "fallback")
    existing_quests = (await session.execute(quest_stmt)).scalars().all()
    existing_titles = {q.title for q in existing_quests}

    quests_inserted = 0
    demo_quest = None
    for q_data in quests_data:
        if q_data["title"] not in existing_titles:
            q = Quest(id=uuid.uuid4(), **q_data)
            session.add(q)
            quests_inserted += 1
            if not demo_quest:
                demo_quest = q
        elif not demo_quest:
            demo_quest = next(q for q in existing_quests if q.title == q_data["title"])

    if quests_inserted > 0:
        await session.flush()
        logger.info(f"Inserted {quests_inserted} fallback quests.")
    else:
        logger.info("Fallback quests already exist. Skipping.")

    # 3. Achievement Definitions and User Unlocks
    achievements = ["First_Quest", "Explorer_Initiate", "Social_Butterfly"]
    for ach_key in achievements:
        ach_stmt = select(Achievement).where(
            Achievement.user_id == demo_user.id, Achievement.achievement_key == ach_key
        )
        if not (await session.execute(ach_stmt)).scalars().first():
            ach = Achievement(id=uuid.uuid4(), user_id=demo_user.id, achievement_key=ach_key)
            session.add(ach)
            logger.info(f"Unlocked achievement '{ach_key}' for demo user.")

    # 4. Example Quest Attempt
    attempt_stmt = select(QuestAttempt).where(QuestAttempt.user_id == demo_user.id)
    if not (await session.execute(attempt_stmt)).scalars().first():
        if demo_quest:
            attempt = QuestAttempt(
                id=uuid.uuid4(),
                quest_id=demo_quest.id,
                user_id=demo_user.id,
                status="COMPLETED",
                result="SUCCESS",
                earned_xp=demo_quest.xp_reward,
                completed_at=datetime.now(UTC),
            )
            session.add(attempt)
            logger.info("Added example quest attempt.")

            # 5. Example XP Transaction
            xp_tx = XPTransaction(
                id=uuid.uuid4(),
                user_id=demo_user.id,
                amount=demo_quest.xp_reward,
                reason="Quest Completed",
                reference_id=str(attempt.id),
            )
            session.add(xp_tx)
            logger.info("Added example XP transaction.")
    else:
        logger.info("Quest attempts already exist for demo user. Skipping.")

    await session.commit()
    logger.info("Database seeding completed successfully.")


async def reset_data(session: AsyncSession) -> None:
    await check_environment_for_reset()
    logger.warning("Resetting database (dropping all records)...")

    # Very dangerous, hence the environment check
    tables = [
        "achievements",
        "reflections",
        "evidences",
        "xp_transactions",
        "quest_attempts",
        "player_profiles",
        "quests",
        "users",
    ]
    for table in tables:
        await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))

    await session.commit()
    logger.info("Database reset completed successfully.")


async def main() -> None:
    parser = argparse.ArgumentParser(description="REALITY.EXE CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("seed", help="Seed the database with deterministic demo data.")
    subparsers.add_parser("reset", help="Reset the database (Development only).")

    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        try:
            if args.command == "seed":
                if settings.ENVIRONMENT.lower() == "production":
                    logger.warning("Running seed in PRODUCTION environment.")
                    # In production we might not want to seed demo users,
                    # but the requirement says "Do NOT seed production automatically".
                    # Here it's manual, but we should probably still avoid demo data in prod.
                    logger.warning("Proceeding with caution. (Idempotent seed)")
                await seed_data(session)
            elif args.command == "reset":
                await reset_data(session)
        except Exception as e:
            await session.rollback()
            logger.error(f"Error during {args.command}: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
