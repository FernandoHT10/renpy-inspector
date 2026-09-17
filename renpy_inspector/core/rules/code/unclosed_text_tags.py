"""Rule detecting unclosed formatting text tags in dialogue lines."""

import re

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.rules.base import BaseRule

# Tags in Ren'Py that enclose content and require an explicit closing tag {/tag}
PAIRED_TAGS = frozenset({
    "b",
    "i",
    "u",
    "s",
    "plain",
    "color",
    "alpha",
    "font",
    "size",
    "outlinecolor",
    "k",
    "cps",
    "a",
    "rb",
    "rt",
})

RE_TEXT_TAG = re.compile(r"\{(/?[a-zA-Z_]\w*)(?:=[^}]*)?\}", re.UNICODE)


class UnclosedTextTagsRule(BaseRule):
    """Detects text formatting tags ({b}, {color=...}, etc.) left unclosed in dialogue."""

    rule_id = "RPY-TEXT-001"
    title = "Unclosed Text Tag in Dialogue"
    category = Category.CODE
    default_severity = Severity.WARNING
    description = (
        "Checks dialogue strings for formatting tags that were opened but not closed "
        "(such as '{b}', '{color=...}', '{size=...}')."
    )

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        for diag in context.all_dialogues:
            text = diag.text
            if "{" not in text or "}" not in text:
                continue

            stack: list[str] = []
            for tag_match in RE_TEXT_TAG.finditer(text):
                raw_tag = tag_match.group(1).lower()
                if raw_tag.startswith("/"):
                    closing = raw_tag[1:]
                    if closing in PAIRED_TAGS:
                        if stack and stack[-1] == closing:
                            stack.pop()
                        elif closing in stack:
                            stack.remove(closing)
                else:
                    if raw_tag in PAIRED_TAGS:
                        stack.append(raw_tag)

            if stack:
                tags_str = ", ".join(f"'{t}'" for t in stack)
                preview = text if len(text) <= 50 else text[:47] + "..."
                closings_sug = "".join(f"{{/{t}}}" for t in reversed(stack))

                msg = (
                    f"Dialogue text contains unclosed formatting tag(s): {tags_str} "
                    f"in \"{preview}\"."
                )
                sug = f"Add the closing tag(s) {closings_sug} before the end of the line."

                issues.append(
                    self.create_issue(
                        message=msg,
                        location=diag.location,
                        suggestion=sug,
                        metadata={
                            "unclosed_tags": stack,
                            "dialogue_text": text,
                        },
                    )
                )

        return issues
