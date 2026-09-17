"""Rule detecting unreachable code statements following unconditional jump or return."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.rules.base import BaseRule


class UnreachableCodeRule(BaseRule):
    """Detects statements that will never execute after unconditional jump or return."""

    rule_id = "RPY-CODE-007"
    title = "Unreachable Code Statement"
    category = Category.CODE
    default_severity = Severity.WARNING
    description = (
        "Checks for dialogue or statements immediately following an unconditional "
        "'jump' or 'return' statement without an intervening label."
    )

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        for unreachable in context.all_unreachables:
            stmt_snippet = unreachable.statement
            if len(stmt_snippet) > 50:
                stmt_snippet = stmt_snippet[:47] + "..."

            msg = (
                f"Statement '{stmt_snippet}' is unreachable because it follows an "
                f"unconditional '{unreachable.preceding_statement}' statement "
                f"(line {unreachable.preceding_line})."
            )
            sug = (
                f"Move this statement before '{unreachable.preceding_statement}', place it under a "
                "label, or remove it if it is dead code."
            )

            issues.append(
                self.create_issue(
                    message=msg,
                    location=unreachable.location,
                    suggestion=sug,
                    metadata={
                        "statement": unreachable.statement,
                        "preceding_statement": unreachable.preceding_statement,
                        "preceding_line": unreachable.preceding_line,
                    },
                )
            )

        return issues
