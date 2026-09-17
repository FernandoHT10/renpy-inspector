"""License and commercial tier capability management."""

import json
import os
from pathlib import Path
from typing import Optional

from renpy_inspector.core.license.tier import Tier


class TierManager:
    """Manages licensing state and feature gate authorizations."""

    _instance: Optional["TierManager"] = None

    def __init__(self, override_tier: Optional[Tier] = None) -> None:
        if override_tier is not None:
            self._tier = override_tier
        else:
            self._tier = self._detect_tier()

    @classmethod
    def get_instance(cls) -> "TierManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current_tier(self) -> Tier:
        return self._tier

    def set_tier(self, tier: Tier) -> None:
        """Dynamically update tier (e.g. upon license activation)."""
        self._tier = tier

    def _detect_tier(self) -> Tier:
        """Detect tier from environment or user config directory."""
        env_tier = os.getenv("RENPY_INSPECTOR_TIER")
        if env_tier:
            return Tier.from_str(env_tier)

        config_file = Path.home() / ".renpy_inspector" / "license.json"
        if config_file.is_file():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return Tier.from_str(data.get("tier", "FREE"))
            except Exception:
                pass

        # Default during development / trial
        return Tier.DEV

    def is_rule_allowed(self, rule_min_tier: Tier) -> bool:
        """Check if a rule with min_tier is permitted under the active tier."""
        return self._tier >= rule_min_tier

    def can_export_html(self) -> bool:
        """Interactive standalone HTML reports require PRO tier or higher."""
        return self._tier >= Tier.PRO

    def can_export_json(self) -> bool:
        """JSON reports require PRO tier or higher."""
        return self._tier >= Tier.PRO

    def can_load_plugins(self) -> bool:
        """Custom third-party Python plugin rules require DEV tier."""
        return self._tier >= Tier.DEV
