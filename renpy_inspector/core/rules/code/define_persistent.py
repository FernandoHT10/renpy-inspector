"""Rule detecting persistent variables declared with define instead of default."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.rules.base import BaseRule


class DefinePersistentRule(BaseRule):
    """Detects 'define persistent.x = ...' which resets persistent data on game launch."""

    rule_id = "RPY-CODE-008"
    title = "Persistent Variable Declared with Define"
    category = Category.CODE
    default_severity = Severity.ERROR
    description = (
        "Checks that persistent variables are declared using 'default persistent.<name>' "
        "rather than 'define'. Using 'define' resets the persistent variable on every game start."
    )

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        for var_name, decl_list in context.defines_by_name.items():
            if var_name.startswith("persistent.") or var_name.startswith("store.persistent."):
                clean_name = var_name.removeprefix("store.")
                for decl in decl_list:
                    msg = (
                        f"Variable '{var_name}' is declared with 'define'. "
                        "Because 'define' executes at startup, this will overwrite "
                        "saved player progress or persistent data every time the game launches."
                    )
                    sug = (
                        f"Replace 'define {var_name} = ...' with 'default {clean_name} = ...' "
                        "to properly preserve persistent state across sessions."
                    )

                    issues.append(
                        self.create_issue(
                            message=msg,
                            location=decl.location,
                            suggestion=sug,
                            metadata={
                                "variable": var_name,
                                "declaration_kind": decl.kind,
                            },
                        )
                    )

        return issues
