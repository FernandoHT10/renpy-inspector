"""Top-level immutable analysis result, coverage, and diagnostic models."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from renpy_inspector.core.models.failures import ParseFailure, RuleFailure, ScanError
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.project import RenPyProject


class AnalysisStatus(str, Enum):
    """Overall state of the static analysis run."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DiagnosticLevel(str, Enum):
    """Severity for infrastructure and operational diagnostics."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class AnalysisDiagnostic:
    """Infrastructure or operational diagnostic (not a game code issue)."""

    level: DiagnosticLevel
    source: str
    message: str
    file_path: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "source": self.source,
            "message": self.message,
            "file_path": self.file_path,
        }


@dataclass(frozen=True)
class AnalysisCoverage:
    """Quantitative observable metrics of the inspection."""

    total_assets_discovered: int
    source_scripts_discovered: int
    compiled_scripts_discovered: int
    parse_attempted: int
    parse_succeeded: int
    parse_failed: int
    rules_registered: int
    rules_executed: int
    rules_failed: int
    unreadable_paths_count: int
    images_discovered: int = 0
    audio_discovered: int = 0
    fonts_discovered: int = 0

    @property
    def parsing_coverage_pct(self) -> Optional[float]:
        """Percentage of discovered source scripts parsed successfully. None if 0 scripts."""
        if self.source_scripts_discovered == 0:
            return None
        return round((self.parse_succeeded / self.source_scripts_discovered) * 100.0, 2)

    @property
    def has_compiled_scripts_without_sources(self) -> bool:
        """True if compiled scripts (.rpyc) exist but no source scripts (.rpy) were found."""
        return self.source_scripts_discovered == 0 and self.compiled_scripts_discovered > 0

    @property
    def is_fully_covered(self) -> bool:
        """True if analysis achieved 100% complete coverage without unobserved/failed areas."""
        return (
            self.parse_failed == 0
            and self.unreadable_paths_count == 0
            and self.rules_failed == 0
            and not self.has_compiled_scripts_without_sources
            and (self.rules_registered == 0 or self.rules_executed == self.rules_registered)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_assets_discovered": self.total_assets_discovered,
            "source_scripts_discovered": self.source_scripts_discovered,
            "compiled_scripts_discovered": self.compiled_scripts_discovered,
            "parse_attempted": self.parse_attempted,
            "parse_succeeded": self.parse_succeeded,
            "parse_failed": self.parse_failed,
            "rules_registered": self.rules_registered,
            "rules_executed": self.rules_executed,
            "rules_failed": self.rules_failed,
            "unreadable_paths_count": self.unreadable_paths_count,
            "images_discovered": self.images_discovered,
            "audio_discovered": self.audio_discovered,
            "fonts_discovered": self.fonts_discovered,
            "parsing_coverage_pct": self.parsing_coverage_pct,
            "is_fully_covered": self.is_fully_covered,
            "has_compiled_scripts_without_sources": self.has_compiled_scripts_without_sources,
        }


@dataclass(frozen=True)
class AnalysisResult:
    """Unified, deeply immutable top-level result of the inspection."""

    project: Optional[RenPyProject]
    status: AnalysisStatus
    issues: tuple[Issue, ...]
    coverage: AnalysisCoverage
    diagnostics: tuple[AnalysisDiagnostic, ...]
    rule_failures: tuple[RuleFailure, ...]
    parse_failures: tuple[ParseFailure, ...]
    scan_errors: tuple[ScanError, ...]
    scan_duration_seconds: float

    @property
    def is_clean(self) -> bool:
        """True only if analysis was 100% COMPLETE and zero issues were detected."""
        return self.status == AnalysisStatus.COMPLETE and len(self.issues) == 0

    @property
    def has_issues(self) -> bool:
        """True if any issues were detected."""
        return len(self.issues) > 0

    @property
    def has_failures(self) -> bool:
        """True if any rule, parse, or scan failures occurred."""
        return (
            len(self.rule_failures) > 0
            or len(self.parse_failures) > 0
            or len(self.scan_errors) > 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project.to_dict() if self.project else None,
            "status": self.status.value,
            "issues_count": len(self.issues),
            "coverage": self.coverage.to_dict(),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "rule_failures": [rf.to_dict() for rf in self.rule_failures],
            "parse_failures": [pf.to_dict() for pf in self.parse_failures],
            "scan_errors": [se.to_dict() for se in self.scan_errors],
            "scan_duration_seconds": self.scan_duration_seconds,
            "is_clean": self.is_clean,
        }
