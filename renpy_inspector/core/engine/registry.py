"""Registry for managing active and available static analysis rules."""

from typing import Optional

from renpy_inspector.core.rules.base import BaseRule


class RuleRegistry:
    """Stores and configures rules available for analysis."""

    def __init__(self) -> None:
        self._rules: dict[str, BaseRule] = {}
        self._enabled: dict[str, bool] = {}

    def register(
        self,
        rule: BaseRule,
        enabled: bool = True,
        allow_override: bool = False,
    ) -> None:
        """Add a rule to the registry.

        Raises:
            ValueError: If a rule with the same ID is already registered and
                allow_override is False.
        """
        rule_id = getattr(rule, "rule_id", rule.__class__.__name__)
        if rule_id in self._rules and not allow_override:
            raise ValueError(
                f"Rule with ID '{rule_id}' is already registered. "
                "Set allow_override=True to explicitly replace it."
            )
        self._rules[rule_id] = rule
        self._enabled[rule_id] = enabled

    def set_enabled(self, rule_id: str, enabled: bool) -> None:
        """Enable or disable a specific rule by ID.

        Raises:
            KeyError: If rule_id is not present in registered rules.
        """
        if rule_id not in self._rules:
            raise KeyError(
                f"Cannot configure unknown rule ID '{rule_id}'. "
                f"Registered rules: {list(self._rules.keys())}"
            )
        self._enabled[rule_id] = enabled

    def is_enabled(self, rule_id: str) -> bool:
        """Check whether a rule is currently enabled."""
        return self._enabled.get(rule_id, False)

    def get_rule(self, rule_id: str) -> Optional[BaseRule]:
        """Retrieve rule by its unique identifier."""
        return self._rules.get(rule_id)

    def get_active_rules(self) -> list[BaseRule]:
        """Return all currently enabled rules."""
        return [
            rule for rule_id, rule in self._rules.items()
            if self._enabled.get(rule_id, True)
        ]

    def get_all_rules(self) -> list[BaseRule]:
        """Return all registered rules."""
        return list(self._rules.values())

    @classmethod
    def create_default(cls) -> "RuleRegistry":
        """Instantiate a registry preloaded with default core rules."""
        from renpy_inspector.core.rules import get_default_rules

        registry = cls()
        for rule in get_default_rules():
            registry.register(rule, enabled=True)
        return registry

    @classmethod
    def default(cls) -> "RuleRegistry":
        """Alias for create_default."""
        return cls.create_default()
