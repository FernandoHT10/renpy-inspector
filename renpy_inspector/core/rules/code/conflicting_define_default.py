"""Rule detecting variables declared with both define and default statements."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.rules.base import BaseRule


class ConflictingDefineDefaultRule(BaseRule):
    """Detects variables declared with both 'define' and 'default' causing savegame bugs."""

    rule_id = "RPY-CODE-004"
    title = "Conflicting Define/Default Declaration"
    category = Category.CODE
    default_severity = Severity.WARNING
    description = (
        "Checks that variables are not declared with both 'define' (constant) "
        "and 'default' (saveable)."
    )

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        common_vars = set(context.defines_by_name.keys()) & set(context.defaults_by_name.keys())

        for var_name in sorted(common_vars):
            defs = context.defines_by_name[var_name]
            defaults = context.defaults_by_name[var_name]

            if defs and defaults:
                def_first = defs[0]
                default_first = defaults[0]

                msg = (
                    f"Variable '{var_name}' is declared as both 'define' "
                    f"({def_first.location}) and 'default' ({default_first.location})."
                )
                sug = (
                    f"Use 'default {var_name}' if the value changes during gameplay, "
                    f"or 'define {var_name}' if it is a constant. Do not use both."
                )

                issues.append(
                    self.create_issue(
                        message=msg,
                        location=default_first.location,
                        suggestion=sug,
                        metadata={
                            "variable": var_name,
                            "define_location": def_first.location.to_dict(),
                            "default_location": default_first.location.to_dict(),
                        },
                    )
                )

        return issues
