"""Asset model for tracking multimedia, fonts, and scripts."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from renpy_inspector.core.models.enums import AssetType


@dataclass(frozen=True)
class AssetInfo:
    """Represents a discovered asset in the project."""

    relative_path: str  # Normalized POSIX path relative to game/ directory
    absolute_path: Path
    asset_type: AssetType
    filename: str
    extension: str  # Lowercase extension including dot (e.g. ".png")
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        """Convert asset info to a JSON-serializable dictionary."""
        return {
            "relative_path": self.relative_path,
            "absolute_path": str(self.absolute_path),
            "asset_type": self.asset_type.value,
            "filename": self.filename,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
        }
