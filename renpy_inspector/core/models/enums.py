"""Enumerations for issue classification, severity, and asset types."""

from enum import Enum


class Severity(str, Enum):
    """Severity levels for detected issues."""

    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class Category(str, Enum):
    """Categorization for grouping issues."""

    CODE = "Code"
    ASSETS = "Assets"
    AUDIO = "Audio"
    IMAGES = "Images"
    TRANSLATION = "Translation"
    REFERENCES = "References"
    STRUCTURE = "Project Structure"


class Confidence(str, Enum):
    """Confidence level of an issue to prevent false alarms."""

    CERTAIN = "CERTAIN"
    SUSPECTED = "SUSPECTED"


class AssetType(str, Enum):
    """Known asset types in a Ren'Py project."""

    SCRIPT = "script"
    IMAGE = "image"
    AUDIO = "audio"
    FONT = "font"
    VIDEO = "video"
    UNKNOWN = "unknown"
