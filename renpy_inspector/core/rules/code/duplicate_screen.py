"""Rule detecting duplicate screen definitions sharing the same variant."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.rules.base import BaseRule


class DuplicateScreenRule(BaseRule):
    """Detects screens defined multiple times with the same variant, causing silent overwrites."""

    rule_id = "RPY-SCREEN-002"
    title = "Duplicate Screen Definition"
    category = Category.CODE
    default_severity = Severity.WARNING
    description = (
        "Checks for screens defined multiple times under the same name and variant. "
        "Ren'Py will silently overwrite previous definitions depending on script loading order."
    )

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        for (screen_name, variant), screens in sorted(
            context.screens_by_name_and_variant.items(),
            key=lambda item: (item[0][0], item[0][1] or "")
        ):
            if len(screens) > 1:
                first_screen = screens[0]
                var_desc = f" (variant '{variant}')" if variant else ""

                for duplicate in screens[1:]:
                    msg = (
                        f"Screen '{screen_name}'{var_desc} is defined multiple times: "
                        f"first at {first_screen.location}, and redefined at {duplicate.location}."
                    )
                    sug = (
                        f"Rename or remove the duplicate screen '{screen_name}', or assign a "
                        "distinct variant (e.g. 'variant \"touch\"') if platform-specific."
                    )

                    issues.append(
                        self.create_issue(
                            message=msg,
                            location=duplicate.location,
                            suggestion=sug,
                            metadata={
                                "screen_name": screen_name,
                                "variant": variant,
                                "first_location": first_screen.location.to_dict(),
                                "duplicate_location": duplicate.location.to_dict(),
                            },
                        )
                    )

        return issues
