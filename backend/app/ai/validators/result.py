"""Validation result types for the quest safety and validation engine.

All validators return lists of ValidationIssue rather than raising exceptions.
The pipeline then decides whether to block or warn based on severity.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    """How serious a validation finding is."""

    HARD_BLOCK = "HARD_BLOCK"  # Quest must never reach the database
    SOFT_BLOCK = "SOFT_BLOCK"  # Should trigger retry / fallback
    WARNING = "WARNING"  # Logged but does not block generation


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation finding from any validator."""

    severity: Severity
    code: str  # machine-readable identifier, e.g. "SAFETY_TRESPASSING"
    field: str  # which quest field triggered this, e.g. "brief", "objectives"
    message: str  # human-readable description

    def is_blocking(self) -> bool:
        return self.severity in (Severity.HARD_BLOCK, Severity.SOFT_BLOCK)


@dataclass
class ValidationReport:
    """Aggregated output from one or more validators."""

    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)

    @property
    def has_hard_blocks(self) -> bool:
        return any(i.severity == Severity.HARD_BLOCK for i in self.issues)

    @property
    def has_soft_blocks(self) -> bool:
        return any(i.severity == Severity.SOFT_BLOCK for i in self.issues)

    @property
    def is_blocking(self) -> bool:
        """True if any issue would prevent persistence."""
        return any(i.is_blocking() for i in self.issues)

    @property
    def hard_blocks(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.HARD_BLOCK]

    @property
    def soft_blocks(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.SOFT_BLOCK]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    def merge(self, other: "ValidationReport") -> "ValidationReport":
        """Return a new report combining self and other."""
        merged = ValidationReport()
        merged.issues = self.issues + other.issues
        return merged

    def to_dict(self) -> dict:
        """Serialise for logging or API responses."""
        return {
            "blocking": self.is_blocking,
            "hard_block_count": len(self.hard_blocks),
            "soft_block_count": len(self.soft_blocks),
            "warning_count": len(self.warnings),
            "issues": [
                {
                    "severity": i.severity,
                    "code": i.code,
                    "field": i.field,
                    "message": i.message,
                }
                for i in self.issues
            ],
        }
