"""Assets rules package."""

from renpy_inspector.core.rules.assets.case_mismatch import CaseMismatchRule
from renpy_inspector.core.rules.assets.invalid_audio_channel import (
    InvalidAudioChannelRule,
)
from renpy_inspector.core.rules.assets.missing_audio import MissingAudioRule
from renpy_inspector.core.rules.assets.missing_font import MissingFontRule
from renpy_inspector.core.rules.assets.missing_image import MissingImageRule
from renpy_inspector.core.rules.assets.unused_asset import UnusedAssetCandidateRule

__all__ = [
    "MissingAudioRule",
    "MissingImageRule",
    "CaseMismatchRule",
    "MissingFontRule",
    "UnusedAssetCandidateRule",
    "InvalidAudioChannelRule",
]
