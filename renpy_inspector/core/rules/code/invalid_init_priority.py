"""Rule detecting init statements and variables using reserved init priorities."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.rules.base import BaseRule

MIN_SAFE_PRIORITY = -999
MAX_SAFE_PRIORITY = 999


class InvalidInitPriorityRule(BaseRule):
    """Detects init blocks, offsets, or defines using priorities outside [-999, 999]."""

    rule_id = "RPY-CODE-010"
    title = "Invalid Init Priority"
    category = Category.CODE
    default_severity = Severity.WARNING
    description = (
        "Checks that init priorities, offsets, and define statements stay within "
        "the safe range for user code (-999 to 999). Priorities outside this range "
        "are reserved for Ren'Py internal engine operations."
    )

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        # 1. Check explicit init blocks and init offset statements
        for stmt in context.all_init_statements:
            if stmt.priority < MIN_SAFE_PRIORITY or stmt.priority > MAX_SAFE_PRIORITY:
                issues.append(
                    self.create_issue(
                        message=(
                            f"Init priority {stmt.priority} in statement '{stmt.statement_type}' "
                            f"is outside the valid user range "
                            f"({MIN_SAFE_PRIORITY} to {MAX_SAFE_PRIORITY}). "
                            "Priorities <= -1000 and >= 1000 are reserved for Ren'Py internal "
                            "engine operations and can lead to undefined initialization ordering."
                        ),
                        location=stmt.location,
                        suggestion=(
                            f"Adjust the priority to a value between {MIN_SAFE_PRIORITY} and "
                            f"{MAX_SAFE_PRIORITY} (e.g., -999 for early library setup or "
                            "-100 to 100 for game code)."
                        ),
                        metadata={
                            "priority": stmt.priority,
                            "statement_type": stmt.statement_type,
                        },
                    )
                )

        # 2. Check define statements with explicit priorities
        for var in context.all_variables:
            if var.priority is not None and (
                var.priority < MIN_SAFE_PRIORITY or var.priority > MAX_SAFE_PRIORITY
            ):
                issues.append(
                    self.create_issue(
                        message=(
                            f"Priority {var.priority} in '{var.kind}' statement for '{var.name}' "
                            f"is outside the valid user range "
                            f"({MIN_SAFE_PRIORITY} to {MAX_SAFE_PRIORITY}). "
                            "Priorities outside this range are reserved for internal operations."
                        ),
                        location=var.location,
                        suggestion=(
                            f"Set priority within {MIN_SAFE_PRIORITY} to {MAX_SAFE_PRIORITY}."
                        ),
                        metadata={
                            "priority": var.priority,
                            "variable": var.name,
                            "kind": var.kind,
                        },
                    )
                )

        return issues
