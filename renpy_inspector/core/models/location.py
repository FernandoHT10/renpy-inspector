"""Location model for pinpointing issues in project files."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class Location:
    """Represents a file location with optional line and column numbers."""

    file_path: str  # Normalized POSIX-style path relative to project root
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    source_snippet: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert location to a JSON-serializable dictionary."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "source_snippet": self.source_snippet,
        }

    def __str__(self) -> str:
        if self.line_number is not None:
            if self.column_number is not None:
                return f"{self.file_path}:{self.line_number}:{self.column_number}"
            return f"{self.file_path}:{self.line_number}"
        return self.file_path
