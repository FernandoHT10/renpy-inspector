"""Domain models and utilities for asset and audio reference resolution."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from renpy_inspector.core.models.asset import AssetInfo

RE_AUDIO_CLAUSE_PREFIX = re.compile(r"^<([^>]+)>\s*")


def parse_audio_target(raw_target: str) -> tuple[tuple[str, ...], str, bool]:
    """Parse a raw audio reference target into clauses, clean target, and quoted flag.

    Args:
        raw_target: Raw target string as extracted from script (e.g. '"<loop 1.0>music/bgm.ogg"'
            or '<volume 0.5> sfx_click' or 'theme').

    Returns:
        A tuple of:
          - clauses: tuple of clause strings (e.g. ("<loop 1.0>",))
          - clean_target: clean file path or identifier without quotes or clauses
          - is_quoted: True if the target was enclosed in quotation marks
    """
    text = raw_target.strip()
    clauses: list[str] = []

    # 1. Extract leading <...> clauses before any quotes
    while True:
        m = RE_AUDIO_CLAUSE_PREFIX.match(text)
        if not m:
            break
        clauses.append(f"<{m.group(1).strip()}>")
        text = text[m.end():].strip()

    is_quoted = False
    # 2. Check if remaining text is quoted
    if (text.startswith('"') and text.endswith('"') and len(text) >= 2) or (
        text.startswith("'") and text.endswith("'") and len(text) >= 2
    ):
        is_quoted = True
        text = text[1:-1].strip()

    # 3. Check for inner clauses inside quotes (e.g. "<loop 1.0 to 2.0>music/song.ogg")
    while True:
        m = RE_AUDIO_CLAUSE_PREFIX.match(text)
        if not m:
            break
        clauses.append(f"<{m.group(1).strip()}>")
        text = text[m.end():].strip()

    # Normalize backslashes to forward slashes for file paths
    clean_target = text.replace("\\", "/")

    return tuple(clauses), clean_target, is_quoted


class ResolutionStatus(str, Enum):
    """Classification of an asset reference resolution."""

    EXACT = "EXACT"  # Exactly matches file path on disk in game/ or game/audio/
    AUDIO_NAMESPACE = "AUDIO_NAMESPACE"  # Matches automatic audio store symbol in game/audio/
    CASE_MISMATCH = "CASE_MISMATCH"  # Exists on disk, but with different letter casing
    AMBIGUOUS = "AMBIGUOUS"  # Multiple candidates compete for the same identifier/path
    MISSING = "MISSING"  # No matching file or symbol exists on disk
    DYNAMIC = "DYNAMIC"  # Dynamic Python variable or expression; not statically resolvable


@dataclass(frozen=True)
class AssetResolution:
    """Immutable, typed result of resolving an asset reference against the project catalog."""

    status: ResolutionStatus
    target: str  # Original reference target string preserved unmodified
    clean_target: str  # Cleaned path or identifier (unquoted, unclausified)
    is_quoted: bool  # True if reference was a quoted string, False if bare identifier
    asset: Optional[AssetInfo] = None  # Populated if EXACT, AUDIO_NAMESPACE, or unambiguous match
    candidates: tuple[AssetInfo, ...] = ()  # Candidates for AMBIGUOUS, CASE_MISMATCH, etc.
    matched_path: Optional[str] = None  # Canonical relative path on disk if resolved
    clauses: tuple[str, ...] = ()  # Audio clauses attached to reference (<loop ...>, etc.)
    suggestion: Optional[str] = None  # Heuristic diagnostic suggestion (e.g. "Did you mean 'x'?")

    def __post_init__(self) -> None:
        """Enforce strict domain invariants across resolution statuses."""
        if self.status in (ResolutionStatus.EXACT, ResolutionStatus.AUDIO_NAMESPACE):
            if self.asset is None or self.matched_path is None:
                raise ValueError(
                    f"{self.status} resolution requires non-None asset and matched_path."
                )
        elif self.status == ResolutionStatus.AMBIGUOUS:
            if len(self.candidates) < 2:
                raise ValueError("AMBIGUOUS resolution requires at least 2 candidates.")
        elif self.status == ResolutionStatus.MISSING:
            if self.asset is not None or self.matched_path is not None:
                raise ValueError("MISSING resolution must not have asset or matched_path.")
        elif self.status == ResolutionStatus.DYNAMIC:
            if self.asset is not None or self.matched_path is not None or len(self.candidates) > 0:
                raise ValueError(
                    "DYNAMIC resolution must not present candidates, asset, or matched_path."
                )
