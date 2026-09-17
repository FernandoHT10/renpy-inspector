"""Rule detecting casing mismatches between code references and filesystem assets."""

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.symbols import ReferenceKind
from renpy_inspector.core.rules.base import BaseRule


class CaseMismatchRule(BaseRule):
    """Detects case-sensitivity discrepancies that crash on Linux/Steam Deck/Android."""

    rule_id = "RPY-REF-001"
    title = "Asset Case Mismatch"
    category = Category.REFERENCES
    default_severity = Severity.WARNING
    description = "Checks that asset path references match the exact disk file casing."

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        # 1. Check image asset references
        for img in context.all_images:
            if img.is_dynamic or not img.asset_reference:
                continue

            ref = img.asset_reference.replace("\\", "/").strip("/")
            mismatch = context.catalog.has_case_mismatch(ref)
            if not mismatch and not context.catalog.find_exact(ref):
                mismatch = context.catalog.has_case_mismatch(f"images/{ref}")

            if mismatch:
                msg = (
                    f"Case mismatch for image '{img.name}': referenced as "
                    f"'{img.asset_reference}', but file on disk is '{mismatch}'. "
                    "Will cause crashes on Linux and Android."
                )
                issues.append(
                    self.create_issue(
                        message=msg,
                        location=img.location,
                        suggestion=f"Update reference to match disk casing '{mismatch}'.",
                        metadata={"referenced": img.asset_reference, "actual": mismatch},
                    )
                )

        # 2. Check audio references
        for audio in context.all_audios:
            if audio.kind == ReferenceKind.DYNAMIC:
                continue

            target = audio.target.strip("\"'").replace("\\", "/")
            if not target:
                continue

            mismatch = context.catalog.has_case_mismatch(target)
            if not mismatch and not context.catalog.find_exact(target):
                mismatch = context.catalog.has_case_mismatch(f"audio/{target}")

            if mismatch:
                msg = (
                    f"Case mismatch for audio file: referenced as '{target}', "
                    f"but file on disk is '{mismatch}'. "
                    "Will cause crashes on Linux and Android."
                )
                issues.append(
                    self.create_issue(
                        message=msg,
                        location=audio.location,
                        suggestion=f"Update reference to match disk casing '{mismatch}'.",
                        metadata={"referenced": target, "actual": mismatch},
                    )
                )

        return issues
