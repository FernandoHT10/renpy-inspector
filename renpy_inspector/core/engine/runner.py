"""Rule runner orchestrating execution of active rules against a ProjectContext."""

from typing import Callable, Optional

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.engine.registry import RuleRegistry
from renpy_inspector.core.models.enums import Severity
from renpy_inspector.core.models.issue import Issue

# Order for sorting severity levels
SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.ERROR: 1,
    Severity.WARNING: 2,
    Severity.INFO: 3,
}


class RuleRunner:
    """Executes registered rules sequentially against a ProjectContext."""

    def __init__(self, registry: Optional[RuleRegistry] = None) -> None:
        self.registry = registry or RuleRegistry.create_default()

    def run(
        self,
        context: ProjectContext,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> list[Issue]:
        """Execute all active rules and return deduplicated, sorted issues."""
        active_rules = self.registry.get_active_rules()
        total_rules = len(active_rules)
        collected_issues: list[Issue] = []
        seen_ids: set[str] = set()

        for idx, rule in enumerate(active_rules, start=1):
            if progress_callback:
                progress_callback(rule.title, idx, total_rules)

            try:
                rule_issues = rule.analyze(context)
                for issue in rule_issues:
                    if issue.id not in seen_ids:
                        seen_ids.add(issue.id)
                        collected_issues.append(issue)
            except Exception:
                # Avoid crashing entire analysis on rule error; could log in future
                continue

        # Sort issues deterministically by severity then location
        collected_issues.sort(
            key=lambda it: (
                SEVERITY_ORDER.get(it.severity, 99),
                it.location.file_path,
                it.location.line_number or 0,
                it.location.column_number or 0,
            )
        )

        return collected_issues
