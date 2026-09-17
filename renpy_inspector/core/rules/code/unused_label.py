"""Rule detecting defined labels that are never jumped to or called."""

from typing import List

from renpy_inspector.core.engine.context import BUILTIN_RENPY_LABELS, ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.rules.base import Rule


class UnusedLabelRule(Rule):
    """Detects defined labels that appear unreferenced and unreachable."""

    rule_id = "RPY-CODE-005"
    title = "Unused Label"
    category = Category.CODE
    default_severity = Severity.INFO
    description = (
        "Checks for defined labels that are never targeted by jump, call, or script references."
    )

    def analyze(self, context: ProjectContext) -> List[Issue]:
        issues: List[Issue] = []

        # Collect targets of all jumps and calls
        jump_targets = {j.target for j in context.all_jumps if not j.is_expression}
        call_targets = {
            c.target for c in context.all_calls if not c.is_screen and not c.is_expression
        }
        targeted = jump_targets | call_targets

        for name, label_list in context.labels_by_name.items():
            # Skip builtins, private labels, and local sub-labels
            if name in BUILTIN_RENPY_LABELS or name.startswith("_") or name.startswith("."):
                continue

            # If referenced via jump/call or present in script token pool (e.g. actions, renpy.jump)
            if name in targeted or name in context.script_token_pool:
                continue

            for lbl in label_list:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=self.default_severity,
                        category=self.category,
                        title=f"Unused Label '{name}'",
                        message=(
                            f"Label '{name}' is defined but is never targeted by any jump, "
                            "call, or known script reference."
                        ),
                        location=lbl.location,
                        suggestion=(
                            f"If '{name}' is dead code, remove it to clean up the project. "
                            "Otherwise, ensure a jump or call directs narrative flow to it."
                        ),
                    )
                )

        return issues
