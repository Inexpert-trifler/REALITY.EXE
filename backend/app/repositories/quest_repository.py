from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quest import Quest
from app.models.quest_attempt import QuestAttempt
from app.repositories.base import BaseRepository


@dataclass
class AttemptStats:
    """Aggregated quest attempt counts for a single user."""

    total: int
    completed: int
    abandoned: int


@dataclass
class ExtendedAttemptStats(AttemptStats):
    """Aggregated stats including play-style and duration data."""

    avg_duration_minutes: float | None
    favorite_play_style: str | None


class QuestRepository(BaseRepository[Quest]):
    """Repository for generated quests."""

    def __init__(self) -> None:
        super().__init__(Quest)

    async def get_recent_quests(self, db: AsyncSession, limit: int = 10) -> Sequence[Quest]:
        """Fetch most recently created quests."""
        result = await db.execute(select(Quest).order_by(Quest.created_at.desc()).limit(limit))
        return result.scalars().all()


class QuestAttemptRepository(BaseRepository[QuestAttempt]):
    """Repository for player quest lifecycle attempts."""

    def __init__(self) -> None:
        super().__init__(QuestAttempt)

    async def get_by_user_id(
        self, db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> Sequence[QuestAttempt]:
        """Fetch quest attempts for a given user ordered by start time."""
        result = await db.execute(
            select(QuestAttempt)
            .where(QuestAttempt.user_id == user_id)
            .order_by(QuestAttempt.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_active_attempt(self, db: AsyncSession, user_id: UUID) -> QuestAttempt | None:
        """Fetch current non-terminal (ACTIVE, POCKET_MODE, etc.) quest attempt for user."""
        active_statuses = [
            "CREATED",
            "ACTIVE",
            "POCKET_MODE",
            "RETURNED",
            "EVIDENCE_PENDING",
            "VERIFYING",
        ]
        result = await db.execute(
            select(QuestAttempt)
            .where(
                QuestAttempt.user_id == user_id,
                QuestAttempt.status.in_(active_statuses),
            )
            .order_by(QuestAttempt.started_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_attempt_stats_by_user_id(self, db: AsyncSession, user_id: UUID) -> AttemptStats:
        """Return aggregated total/completed/abandoned counts for a user."""
        # Single round-trip using conditional aggregation
        result = await db.execute(
            select(
                func.count(QuestAttempt.id).label("total"),
                func.count(QuestAttempt.id)
                .filter(QuestAttempt.status == "COMPLETED")
                .label("completed"),
                func.count(QuestAttempt.id)
                .filter(QuestAttempt.status == "ABANDONED")
                .label("abandoned"),
            ).where(QuestAttempt.user_id == user_id)
        )
        row = result.one()
        return AttemptStats(
            total=row.total,
            completed=row.completed,
            abandoned=row.abandoned,
        )

    async def get_extended_stats_by_user_id(
        self, db: AsyncSession, user_id: UUID
    ) -> ExtendedAttemptStats:
        """Return aggregated counts + avg duration + favourite play style."""
        # Base counts
        counts_result = await db.execute(
            select(
                func.count(QuestAttempt.id).label("total"),
                func.count(QuestAttempt.id)
                .filter(QuestAttempt.status == "COMPLETED")
                .label("completed"),
                func.count(QuestAttempt.id)
                .filter(QuestAttempt.status == "ABANDONED")
                .label("abandoned"),
            ).where(QuestAttempt.user_id == user_id)
        )
        row = counts_result.one()

        # Average duration of COMPLETED quests (via joined Quest.duration_minutes)
        avg_result = await db.execute(
            select(func.avg(Quest.duration_minutes))
            .join(QuestAttempt, QuestAttempt.quest_id == Quest.id)
            .where(
                QuestAttempt.user_id == user_id,
                QuestAttempt.status == "COMPLETED",
            )
        )
        avg_dur = avg_result.scalar_one_or_none()

        # Favourite play_style among COMPLETED quests
        style_result = await db.execute(
            select(Quest.play_style, func.count(Quest.play_style).label("cnt"))
            .join(QuestAttempt, QuestAttempt.quest_id == Quest.id)
            .where(
                QuestAttempt.user_id == user_id,
                QuestAttempt.status == "COMPLETED",
            )
            .group_by(Quest.play_style)
            .order_by(func.count(Quest.play_style).desc())
            .limit(1)
        )
        style_row = style_result.one_or_none()

        return ExtendedAttemptStats(
            total=row.total,
            completed=row.completed,
            abandoned=row.abandoned,
            avg_duration_minutes=round(float(avg_dur), 1) if avg_dur is not None else None,
            favorite_play_style=style_row[0] if style_row else None,
        )

    async def count_completed_by_play_style(
        self, db: AsyncSession, user_id: UUID, play_style: str
    ) -> int:
        """Count COMPLETED attempts for a specific play style."""
        result = await db.execute(
            select(func.count(QuestAttempt.id))
            .join(QuestAttempt.quest)
            .where(
                QuestAttempt.user_id == user_id,
                QuestAttempt.status == "COMPLETED",
                Quest.play_style == play_style,
            )
        )
        return result.scalar_one()

    async def count_completed_outdoor(self, db: AsyncSession, user_id: UUID) -> int:
        """Count COMPLETED attempts for outdoor environments.

        Outdoor environments are those NOT in the explicit indoor set.
        """
        indoor_environments = {"surprise"}  # only 'surprise' is ambiguous; rest are outdoor
        outdoor_envs = ["campus", "park", "neighborhood", "trail", "city", "any"]
        result = await db.execute(
            select(func.count(QuestAttempt.id))
            .join(QuestAttempt.quest)
            .where(
                QuestAttempt.user_id == user_id,
                QuestAttempt.status == "COMPLETED",
                Quest.environment.in_(outdoor_envs),
            )
        )
        return result.scalar_one()

    async def count_completed_with_pocket_mode(self, db: AsyncSession, user_id: UUID) -> int:
        """Count COMPLETED attempts where the player used Pocket Mode
        (pocket_started_at IS NOT NULL) — proxy for pocket_player achievement.
        """
        result = await db.execute(
            select(func.count(QuestAttempt.id)).where(
                QuestAttempt.user_id == user_id,
                QuestAttempt.status == "COMPLETED",
                QuestAttempt.pocket_started_at.is_not(None),
            )
        )
        return result.scalar_one()

    async def get_by_user_id_with_quest(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
        status_filter: str | None = None,
        sort_by: str = "started_at",
        sort_dir: str = "desc",
    ) -> tuple[list[QuestAttempt], int]:
        """Fetch attempts with quest eagerly loaded, plus total count.

        Args:
            status_filter: Optional status string to filter by (e.g. "COMPLETED").
            sort_by:       Column to sort by: "started_at" | "completed_at" | "earned_xp".
            sort_dir:      "asc" or "desc".

        Returns:
            (attempts, total_count)
        """
        sort_col_map = {
            "started_at": QuestAttempt.started_at,
            "completed_at": QuestAttempt.completed_at,
            "earned_xp": QuestAttempt.earned_xp,
        }
        sort_col = sort_col_map.get(sort_by, QuestAttempt.started_at)
        order = sort_col.asc() if sort_dir == "asc" else sort_col.desc()

        base_where = [QuestAttempt.user_id == user_id]
        if status_filter:
            base_where.append(QuestAttempt.status == status_filter.upper())

        count_result = await db.execute(select(func.count(QuestAttempt.id)).where(*base_where))
        total = count_result.scalar_one()

        rows = await db.execute(
            select(QuestAttempt)
            .where(*base_where)
            .options(selectinload(QuestAttempt.quest))
            .order_by(order)
            .offset(skip)
            .limit(limit)
        )
        attempts = list(rows.scalars().all())
        return attempts, total
