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
        effective_paired = (PAIRED_TAGS | {t.lower() for t in context.custom_text_tags}) - {
            t.lower() for t in context.custom_self_closing_text_tags
        }

        for diag in context.all_dialogues:
            text = diag.text
            if "{" not in text or "}" not in text:
                continue

            # In Ren'Py text syntax, '{{' escapes '{' and '}}' escapes '}'.
            clean_text = text.replace("{{", "\u0001").replace("}}", "\u0002")
            if "{" not in clean_text or "}" not in clean_text:
                continue

            stack: list[tuple[str, bool]] = []
            last_end = 0
            has_seen_text = False

            for tag_match in RE_TEXT_TAG.finditer(clean_text):
                between = clean_text[last_end : tag_match.start()]
                cleaned_between = (
                    between.replace("\\n", "")
                    .replace("\\t", "")
                    .replace("\\r", "")
                    .replace("\n", "")
                    .replace("\r", "")
                    .replace("\t", "")
                    .strip(" \t\r\n\\")
                )
                if cleaned_between:
                    has_seen_text = True
                last_end = tag_match.end()

                raw_tag = tag_match.group(1).lower()
                if raw_tag.startswith("/"):
                    closing = raw_tag[1:]
                    if closing in effective_paired:
                        idx = -1
                        for i in range(len(stack) - 1, -1, -1):
                            if stack[i][0] == closing:
                                idx = i
                                break
                        if idx != -1:
                            stack.pop(idx)
                else:
                    if raw_tag in effective_paired:
                        stack.append((raw_tag, not has_seen_text))

            # Tags opened before any visible dialogue text (is_prefix == True)
            # apply to the entire line and are automatically closed by Ren'Py
            # when the displayable ends. Only tags opened inline mid-sentence
            # (is_prefix == False) that remain unclosed are reported as issues.
            unclosed = [t for t, is_prefix in stack if not is_prefix]

            if unclosed:
                tags_str = ", ".join(f"'{t}'" for t in unclosed)
                preview = text if len(text) <= 50 else text[:47] + "..."
                closings_sug = "".join(f"{{/{t}}}" for t in reversed(unclosed))

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
                            "unclosed_tags": unclosed,
                            "dialogue_text": text,
                        },
                    )
                )

        return issues
