"""Provider-independent AI interfaces.

Product logic must only import from this module — never from a specific
provider.  Swapping the underlying model requires only a new provider
class and a wiring change in dependencies.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Data objects shared by all providers
# ---------------------------------------------------------------------------


@dataclass
class QuestGenerationRequest:
    """All inputs the Game Master model needs to produce one quest."""

    duration_minutes: int
    environment: str
    difficulty: str
    play_style: str
    personality: str
    player_level: int = 1
    previous_quest_titles: list[str] = field(default_factory=list)


@dataclass
class RawModelOutput:
    """Raw text returned by a model call, plus provenance metadata."""

    text: str  # The raw string the model emitted
    model_name: str  # e.g. "llama3", "gemma3:4b"
    prompt_version: str  # e.g. "quest_v1"
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class EvidenceAnalysisRequest:
    """Inputs for a vision-model evidence check."""

    image_bytes: bytes
    mime_type: str  # e.g. "image/jpeg"
    quest_brief: str
    quest_objectives: list[dict]


@dataclass
class EvidenceAnalysisResult:
    """Structured output from the vision judge."""

    visible_content: str  # What the model sees
    is_relevant: bool
    confidence: float  # 0.0 – 1.0
    safety_concerns: list[str]
    completion_recommendation: bool
    model_name: str
    model_version: str


@dataclass
class ReflectionRequest:
    """Inputs for the reflection engine."""

    quest_title: str
    quest_brief: str
    outcome: str  # "success" | "abandoned" | "failed"
    earned_xp: int
    personality: str
    # Optional enrichment — callers that don't supply these get basic reflections
    evidence_findings: str = ""  # summary of what the vision model saw
    player_level: int = 1
    quest_difficulty: str = "chill"
    previous_quest_count: int = 0  # total completed quests by this player


# ---------------------------------------------------------------------------
# Abstract provider interfaces
# ---------------------------------------------------------------------------


class TextModelProvider(ABC):
    """Interface every text-generation backend must implement."""

    @abstractmethod
    async def generate_quest(self, request: QuestGenerationRequest) -> RawModelOutput:
        """Call the model and return its raw text response for quest generation.

        The caller is responsible for parsing and validating the output.
        This method must not raise on model errors — it must return the
        raw text or raise a specific ProviderError.
        """

    @abstractmethod
    async def generate_reflection(self, request: ReflectionRequest) -> RawModelOutput:
        """Generate a short narrative reflection after quest completion."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the underlying model (for logging / audit trail)."""


class VisionModelProvider(ABC):
    """Interface every vision-analysis backend must implement."""

    @abstractmethod
    async def analyze_evidence(self, request: EvidenceAnalysisRequest) -> EvidenceAnalysisResult:
        """Analyse submitted evidence and return structured findings."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the underlying model."""


# ---------------------------------------------------------------------------
# Provider errors
# ---------------------------------------------------------------------------


class ProviderError(Exception):
    """Raised when the model backend returns an unrecoverable error."""


class ProviderUnavailableError(ProviderError):
    """The model backend is not reachable (connection refused, timeout, etc.)."""


class ProviderOutputError(ProviderError):
    """The model returned output that cannot be used (empty, unexpected format)."""
