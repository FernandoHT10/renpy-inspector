"""Rule detecting call screen invocations pointing to nonexistent screens."""

from typing import List

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.rules.base import Rule


class UndefinedScreenRule(Rule):
    """Detects screen calls where the target screen is not defined."""

    rule_id = "RPY-SCREEN-001"
    title = "Undefined Screen"
    category = Category.CODE
    default_severity = Severity.ERROR
    description = (
        "Checks that screen names referenced via screen statements "
        "('call screen', 'show screen', 'hide screen') exist in the project or builtins."
    )

    def analyze(self, context: ProjectContext) -> List[Issue]:
        issues: List[Issue] = []

        for call in context.all_calls:
            if not call.is_screen or call.is_expression:
                continue

            screen_name = call.target.strip()
            if not screen_name:
                continue

            if screen_name not in context.defined_screens:
                is_hide = call.screen_action == "hide"
                severity = Severity.WARNING if is_hide else Severity.ERROR
                action_desc = (
                    f"'{call.screen_action} screen'"
                    if call.screen_action
                    else "'screen statement'"
                )
                if is_hide:
                    message = (
                        f"Screen '{screen_name}' referenced via {action_desc} is not defined "
                        "in any script file. In Ren'Py, hiding an undefined screen does not crash "
                        "at runtime, but indicates obsolete cleanup or an unmatched "
                        "screen/tag name."
                    )
                    suggestion = (
                        f"Verify if 'screen {screen_name}:' was renamed, or remove this obsolete "
                        f"{action_desc} statement."
                    )
                else:
                    message = (
                        f"Screen '{screen_name}' referenced via {action_desc} is not defined "
                        "in any script file or Ren'Py standard screens. Reaching this statement "
                        f"will cause a fatal runtime crash: 'ScreenNotFound: {screen_name}'."
                    )
                    suggestion = (
                        f"Define 'screen {screen_name}:' in your screens.rpy or correct "
                        "the screen name if misspelled."
                    )

                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        category=self.category,
                        title=f"Undefined Screen '{screen_name}'",
                        message=message,
                        location=call.location,
                        suggestion=suggestion,
                    )
                )

        return issues
