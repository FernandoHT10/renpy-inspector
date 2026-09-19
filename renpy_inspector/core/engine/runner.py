import traceback as tb_module
from dataclasses import dataclass
from typing import Callable, Optional

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.engine.registry import RuleRegistry
from renpy_inspector.core.models.enums import Severity
from renpy_inspector.core.models.failures import RuleFailure
from renpy_inspector.core.models.issue import Issue

# Order for sorting severity levels
SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.ERROR: 1,
    Severity.WARNING: 2,
    Severity.INFO: 3,
}


@dataclass(frozen=True)
class RunnerResult:
    """Comprehensive, immutable result of the rule runner execution."""

    issues: tuple[Issue, ...]
    failures: tuple[RuleFailure, ...]
    executed_rules_count: int
    total_rules_count: int

    @property
    def has_failures(self) -> bool:
        """True if one or more rules raised an unhandled exception."""
        return len(self.failures) > 0

    @property
    def is_complete(self) -> bool:
        """True if all rules executed with zero failures."""
        return (not self.has_failures) and (self.executed_rules_count == self.total_rules_count)


class RuleRunner:
    """Orchestrates the sequential execution of registered rules."""

    def __init__(self, registry: Optional[RuleRegistry] = None) -> None:
        self.registry = registry or RuleRegistry.create_default()

    def run(
        self,
        context: ProjectContext,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        fail_fast: bool = False,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> RunnerResult:
        """Execute active rules and return a RunnerResult with issues and recorded failures."""
        active_rules = self.registry.get_active_rules()
        total_rules = len(active_rules)
        collected_issues: list[Issue] = []
        collected_failures: list[RuleFailure] = []
        seen_ids: set[str] = set()
        executed_count = 0

        for idx, rule in enumerate(active_rules, start=1):
            if is_cancelled and is_cancelled():
                break

            if progress_callback:
                progress_callback(rule.title, idx, total_rules)

            try:
                rule_issues = rule.analyze(context)
                for issue in rule_issues:
                    if issue.id not in seen_ids:
                        seen_ids.add(issue.id)
                        collected_issues.append(issue)
                executed_count += 1
            except Exception as exc:
                if fail_fast:
                    raise
                formatted_tb = tb_module.format_exc()
                rule_id = getattr(rule, "rule_id", rule.__class__.__name__)
                rule_title = getattr(rule, "title", rule.__class__.__name__)
                collected_failures.append(
                    RuleFailure(
                        rule_id=rule_id,
                        rule_title=rule_title,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                        traceback=formatted_tb,
                    )
                )

        # Sort issues deterministically by severity then location
        collected_issues.sort(
            key=lambda it: (
                SEVERITY_ORDER.get(it.severity, 99),
                it.location.file_path,
                it.location.line_number or 0,
                it.location.column_number or 0,
            )
        )

        return RunnerResult(
            issues=tuple(collected_issues),
            failures=tuple(collected_failures),
            executed_rules_count=executed_count,
            total_rules_count=total_rules,
        )

