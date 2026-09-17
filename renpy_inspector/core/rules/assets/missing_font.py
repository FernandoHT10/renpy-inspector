"""Rule detecting font file references configured in variables that do not exist."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import AssetType, Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.parser.rpy_parser import unquote_string
from renpy_inspector.core.rules.base import BaseRule

# Ren'Py built-in runtime fonts distributed in renpy/common/
BUILTIN_FONTS = frozenset({
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    "TwemojiCOLRv0.ttf",
    "_OpenDyslexic3-Regular.ttf",
    "Quicksand-Bold.ttf",
    "Quicksand-Regular.ttf",
})


class MissingFontRule(BaseRule):
    """Detects missing font files configured in gui/options variables (e.g. gui.text_font)."""

    rule_id = "RPY-FONT-001"
    title = "Missing Font File"
    category = Category.ASSETS
    default_severity = Severity.ERROR
    description = "Checks that font files referenced in gui and script configurations exist."

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        for var in context.all_variables:
            # Check variables that configure fonts
            if "font" in var.name.lower():
                raw = var.raw_value.strip()
                unquoted = unquote_string(raw)
                if not unquoted:
                    continue

                clean_path = unquoted.replace("\\", "/").strip("/")
                clean_name = clean_path.split("/")[-1]

                # Check if it's a standard Ren'Py built-in font
                if clean_name in BUILTIN_FONTS or clean_path in BUILTIN_FONTS:
                    continue

                # Look for font file directly, in fonts/, or in gui/
                found = (
                    context.catalog.find_exact(clean_path)
                    or context.catalog.find_exact(f"fonts/{clean_path}")
                    or context.catalog.find_exact(f"gui/{clean_path}")
                    or context.catalog.find_case_insensitive(clean_path)
                    or context.catalog.find_case_insensitive(f"fonts/{clean_path}")
                )

                if found and found.asset_type == AssetType.FONT:
                    continue

                if not found:
                    msg = (
                        f"Font file '{unquoted}' configured in variable '{var.name}' "
                        "was not found on disk."
                    )
                    sug = f"Place '{unquoted}' in 'game/fonts/' or correct the path."
                    meta = {"variable": var.name, "font_path": unquoted}

                    issues.append(
                        self.create_issue(
                            message=msg,
                            location=var.location,
                            suggestion=sug,
                            metadata=meta,
                        )
                    )

        return issues
