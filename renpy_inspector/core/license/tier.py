"""Commercial edition and feature tier definitions."""

from enum import Enum
from functools import total_ordering


@total_ordering
class Tier(str, Enum):
    """Commercial product tiers with increasing feature capabilities."""

    FREE = "FREE"
    PRO = "PRO"
    DEV = "DEV"

    def _tier_level(self) -> int:
        levels = {
            Tier.FREE: 1,
            Tier.PRO: 2,
            Tier.DEV: 3,
        }
        return levels.get(self, 1)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Tier):
            return self._tier_level() < other._tier_level()
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Tier):
            return self._tier_level() >= other._tier_level()
        return NotImplemented

    @classmethod
    def from_str(cls, val: str) -> "Tier":
        clean = (val or "").strip().upper()
        if clean in ("PRO", "PROFESSIONAL"):
            return cls.PRO
        if clean in ("DEV", "DEVELOPER", "ENTERPRISE"):
            return cls.DEV
        return cls.FREE
