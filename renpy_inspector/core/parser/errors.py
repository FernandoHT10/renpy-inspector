"""Error models for parsing failures and warnings."""

from dataclasses import dataclass
from typing import Any, Optional

from renpy_inspector.core.models.enums import Severity
from renpy_inspector.core.models.location import Location


@dataclass(frozen=True)
class ParseError:
    """Represents a recoverable error or warning encountered during parsing."""

    file_path: str
    line: int
    message: str
    column: Optional[int] = None
    severity: Severity = Severity.WARNING
    source_snippet: Optional[str] = None

    @property
    def location(self) -> Location:
        return Location(
            file_path=self.file_path,
            line_number=self.line,
            column_number=self.column,
            source_snippet=self.source_snippet,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "severity": self.severity.value,
            "source_snippet": self.source_snippet,
        }
