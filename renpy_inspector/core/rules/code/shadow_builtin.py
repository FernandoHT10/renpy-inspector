"""Rule detecting define or default statements that shadow Ren'Py reserved identifiers."""

from typing import List

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.rules.base import Rule

RESERVED_RENPY_NAMES = frozenset(
    {
        "renpy",
        "config",
        "gui",
        "persistent",
        "preferences",
        "store",
        "ui",
        "theme",
        "style",
        "_preferences",
        "_window",
        "_rollback",
        "_confirm_quit",
        "_game_menu_screen",
        "_history",
    }
)


class ShadowBuiltinRule(Rule):
    """Detects define or default variables that override core Ren'Py builtins."""

    rule_id = "RPY-CODE-006"
    title = "Shadowed Ren'Py Built-in"
    category = Category.CODE
    default_severity = Severity.WARNING
    description = (
        "Checks that user variables do not shadow reserved Ren'Py engine objects or globals."
    )

    def analyze(self, context: ProjectContext) -> List[Issue]:
        issues: List[Issue] = []

        for var in context.all_variables:
            # If user defines the exact reserved root name rather than config.name
            if var.name in RESERVED_RENPY_NAMES:
                is_crit = var.name in {"renpy", "store", "gui"}
                sev = Severity.CRITICAL if is_crit else Severity.WARNING
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=sev,
                        category=self.category,
                        title=f"Reserved Identifier '{var.name}' Shadowed",
                        message=(
                            f"Variable '{var.name}' shadows a reserved Ren'Py engine identifier. "
                            "This can break core engine functionality."
                        ),
                        location=var.location,
                        suggestion=(
                            f"Rename '{var.name}' to a project-specific name "
                            "to avoid conflicting with Ren'Py builtins."
                        ),
                    )
                )

        return issues
