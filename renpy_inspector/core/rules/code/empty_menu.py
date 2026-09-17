"""Rule detecting empty menu statements without selectable choices."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.rules.base import BaseRule


class EmptyMenuRule(BaseRule):
    """Detects menu blocks without selectable choices which cause a fatal runtime crash."""

    rule_id = "RPY-CODE-009"
    title = "Empty Menu Statement"
    category = Category.CODE
    default_severity = Severity.ERROR
    description = (
        "Checks that menu blocks contain at least one selectable choice item. "
        "An empty menu raises a fatal Ren'Py runtime exception."
    )

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        for menu in context.all_menus:
            if menu.item_count == 0:
                scope_info = f" in label '{menu.scope_label}'" if menu.scope_label else ""
                msg = (
                    f"Menu block{scope_info} does not contain any selectable choice items. "
                    "Reaching this menu during gameplay will cause a fatal runtime error: "
                    "'Exception: The menu does not contain any choices.'"
                )
                sug = (
                    "Add at least one choice option with a dialogue caption (e.g. '\"Option\":') "
                    "or remove the empty menu statement."
                )

                issues.append(
                    self.create_issue(
                        message=msg,
                        location=menu.location,
                        suggestion=sug,
                        metadata={
                            "item_count": menu.item_count,
                            "scope_label": menu.scope_label,
                        },
                    )
                )

        return issues
