"""Models representing a Ren'Py project and validation outcome."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating whether a directory is a valid Ren'Py project."""

    is_valid: bool
    root_path: Path
    game_path: Optional[Path] = None
    detected_markers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Convert validation result to a JSON-serializable dictionary."""
        return {
            "is_valid": self.is_valid,
            "root_path": str(self.root_path),
            "game_path": str(self.game_path) if self.game_path else None,
            "detected_markers": list(self.detected_markers),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class RenPyProject:
    """Represents an initialized Ren'Py project."""

    name: str
    root_path: Path
    game_path: Path
    is_valid: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert project info to a JSON-serializable dictionary."""
        return {
            "name": self.name,
            "root_path": str(self.root_path),
            "game_path": str(self.game_path),
            "is_valid": self.is_valid,
        }
