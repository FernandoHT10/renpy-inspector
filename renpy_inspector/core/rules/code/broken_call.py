"""Rule detecting call statements that target nonexistent labels."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.symbols import ReferenceKind
from renpy_inspector.core.rules.base import BaseRule


class BrokenCallRule(BaseRule):
    """Detects call statements targeting nonexistent labels, ignoring screens and dynamics."""

    rule_id = "RPY-CODE-002"
    title = "Broken Call Target"
    category = Category.CODE
    default_severity = Severity.ERROR
    description = "Checks that call statements refer to defined labels."

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        for call in context.all_calls:
            # Skip screen calls and dynamic expressions
            if call.is_screen or call.kind == ReferenceKind.DYNAMIC or call.is_expression:
                continue

            target = call.target.strip()
            if not target:
                continue

            is_defined = context.has_label(target, scope=call.scope_label)
            if not is_defined:
                issues.append(
                    self.create_issue(
                        message=f"Call target label '{target}' is not defined in any script.",
                        location=call.location,
                        suggestion=f"Define 'label {target}:' or correct the call target.",
                        metadata={"target": target, "scope": call.scope_label},
                    )
                )

        return issues
