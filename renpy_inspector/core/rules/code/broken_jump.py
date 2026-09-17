"""Rule detecting jump statements that target nonexistent labels."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.symbols import ReferenceKind
from renpy_inspector.core.rules.base import BaseRule


class BrokenJumpRule(BaseRule):
    """Detects jumps targeting nonexistent labels while safely ignoring dynamic expressions."""

    rule_id = "RPY-CODE-001"
    title = "Broken Jump Target"
    category = Category.CODE
    default_severity = Severity.ERROR
    description = "Checks that jump targets refer to existing labels in the project."

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        for jump in context.all_jumps:
            # Skip dynamic expressions (e.g. jump expression var) to avoid false positives
            if jump.kind == ReferenceKind.DYNAMIC or jump.is_expression:
                continue

            target = jump.target.strip()
            if not target:
                continue

            is_defined = context.has_label(target, scope=jump.scope_label)
            if not is_defined:
                if target.startswith("."):
                    scope_info = (
                        f"scoped to '{jump.scope_label}'"
                        if jump.scope_label
                        else "no active scope"
                    )
                    msg = f"The local target label '{target}' ({scope_info}) does not exist."
                    sug = f"Create 'label {target}:' within '{jump.scope_label}' or fix the jump."
                else:
                    msg = f"The target label '{target}' could not be found in any script file."
                    sug = f"Check the spelling or define 'label {target}:'."

                issues.append(
                    self.create_issue(
                        message=msg,
                        location=jump.location,
                        suggestion=sug,
                        metadata={"target": target, "scope": jump.scope_label},
                    )
                )

        return issues
