"""Domain models for Ren'Py Inspector."""

from renpy_inspector.core.models.asset import AssetInfo
from renpy_inspector.core.models.enums import AssetType, Category, Confidence, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.location import Location
from renpy_inspector.core.models.project import RenPyProject, ValidationResult
from renpy_inspector.core.models.symbols import (
    AudioReference,
    CallReference,
    ImageDefinition,
    ImageSymbol,
    InitStatement,
    JumpReference,
    LabelSymbol,
    PythonBlock,
    ReferenceKind,
    ScreenDefinition,
    TranslateBlock,
    VariableDeclaration,
)

__all__ = [
    "Severity",
    "Category",
    "Confidence",
    "AssetType",
    "Location",
    "Issue",
    "AssetInfo",
    "ValidationResult",
    "RenPyProject",
    "LabelSymbol",
    "JumpReference",
    "CallReference",
    "ImageDefinition",
    "ImageSymbol",
    "AudioReference",
    "VariableDeclaration",
    "TranslateBlock",
    "PythonBlock",
    "ReferenceKind",
    "ScreenDefinition",
    "InitStatement",
]
