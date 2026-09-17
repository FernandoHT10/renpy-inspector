"""Rule definitions and registration for Ren'Py Inspector."""

from renpy_inspector.core.rules.assets import (
    CaseMismatchRule,
    InvalidAudioChannelRule,
    MissingAudioRule,
    MissingFontRule,
    MissingImageRule,
    UnusedAssetCandidateRule,
)
from renpy_inspector.core.rules.base import BaseRule
from renpy_inspector.core.rules.code import (
    BrokenCallRule,
    BrokenJumpRule,
    ConflictingDefineDefaultRule,
    DuplicateLabelRule,
    ShadowBuiltinRule,
    UndefinedScreenRule,
    UnusedLabelRule,
)
from renpy_inspector.core.rules.translation import MissingTranslationRule


def get_default_rules() -> list[BaseRule]:
    """Instantiate and return all built-in core and extended analysis rules."""
    return [
        BrokenJumpRule(),
        BrokenCallRule(),
        DuplicateLabelRule(),
        ConflictingDefineDefaultRule(),
        MissingAudioRule(),
        MissingImageRule(),
        CaseMismatchRule(),
        MissingFontRule(),
        MissingTranslationRule(),
        UnusedAssetCandidateRule(),
        UnusedLabelRule(),
        UndefinedScreenRule(),
        InvalidAudioChannelRule(),
        ShadowBuiltinRule(),
    ]


__all__ = [
    "BaseRule",
    "BrokenJumpRule",
    "BrokenCallRule",
    "DuplicateLabelRule",
    "ConflictingDefineDefaultRule",
    "MissingAudioRule",
    "MissingImageRule",
    "CaseMismatchRule",
    "MissingFontRule",
    "MissingTranslationRule",
    "UnusedAssetCandidateRule",
    "UnusedLabelRule",
    "UndefinedScreenRule",
    "InvalidAudioChannelRule",
    "ShadowBuiltinRule",
    "get_default_rules",
]
