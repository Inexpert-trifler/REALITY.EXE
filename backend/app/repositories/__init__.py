"""Repositories package exporting data access classes."""

from app.repositories.base import BaseRepository
from app.repositories.evidence_repository import AIAnalysisRepository, EvidenceRepository
from app.repositories.progression_repository import (
    AchievementRepository,
    XPTransactionRepository,
)
from app.repositories.quest_repository import QuestAttemptRepository, QuestRepository
from app.repositories.reflection_repository import ReflectionRepository
from app.repositories.user_repository import PlayerProfileRepository, UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "PlayerProfileRepository",
    "QuestRepository",
    "QuestAttemptRepository",
    "EvidenceRepository",
    "AIAnalysisRepository",
    "XPTransactionRepository",
    "AchievementRepository",
    "ReflectionRepository",
]
