"""Rule detecting duplicate label declarations across the project."""

from collections import defaultdict

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.symbols import LabelSymbol
from renpy_inspector.core.rules.base import BaseRule


class DuplicateLabelRule(BaseRule):
    """Detects duplicate label definitions which cause ambiguous jumps or crashes in Ren'Py."""

    rule_id = "RPY-CODE-003"
    title = "Duplicate Label Definition"
    category = Category.CODE
    default_severity = Severity.ERROR
    description = "Checks that labels are uniquely defined across all script files."

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        # Group by fully-qualified name so local labels under different scopes don't clash
        by_full_name: dict[str, list[LabelSymbol]] = defaultdict(list)
        for label_list in context.labels_by_name.values():
            for lbl in label_list:
                by_full_name[lbl.full_name].append(lbl)

        for full_name, defs in by_full_name.items():
            if len(defs) > 1:
                # Sort deterministically by file and line
                sorted_defs = sorted(
                    defs,
                    key=lambda item: (item.location.file_path, item.location.line_number or 0),
                )
                first_def = sorted_defs[0]

                # Report all duplicate occurrences after the first
                for dup in sorted_defs[1:]:
                    first_loc_str = str(first_def.location)
                    issues.append(
                        self.create_issue(
                            message=(
                                f"Label '{full_name}' is defined multiple times "
                                f"(previously defined in {first_loc_str})."
                            ),
                            location=dup.location,
                            suggestion=f"Rename label '{full_name}' to make it uniquely named.",
                            metadata={
                                "label_name": full_name,
                                "original_location": first_def.location.to_dict(),
                            },
                        )
                    )

        return issues
