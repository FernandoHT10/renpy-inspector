"""Rule identifying candidate assets that have no detected static references in scripts."""

from pathlib import Path

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import AssetType, Category, Confidence, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.location import Location
from renpy_inspector.core.rules.base import BaseRule


class UnusedAssetCandidateRule(BaseRule):
    """Detects candidate image, audio, and font files that appear to have no static references."""

    rule_id = "RPY-ASSET-001"
    title = "Potentially Unused Asset"
    category = Category.ASSETS
    default_severity = Severity.INFO
    description = (
        "Reports assets with no static references in script files (may be loaded dynamically)."
    )

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []

        # Do not flag assets as unused if no .rpy source files were parsed
        # (e.g. in compiled distributions containing only .rpyc files or SDK translation stubs)
        has_rpy_sources = any(
            f.lower().endswith(".rpy") for f in context.parsed_project.files.keys()
        )
        if not has_rpy_sources:
            return issues

        # Collect all reference strings/tokens in a unified lookup set
        token_pool = context.script_token_pool

        for asset in context.catalog.all_assets():
            # Only analyze images, audio, and fonts
            if asset.asset_type not in (AssetType.IMAGE, AssetType.AUDIO, AssetType.FONT):
                continue

            rel_path = asset.relative_path
            posix_path = rel_path.replace("\\", "/")
            filename = asset.filename
            stem = Path(filename).stem
            stem_spaces = stem.replace("_", " ")

            # O(1) set membership checks against indexed tokens
            is_referenced = (
                rel_path in token_pool
                or posix_path in token_pool
                or rel_path.lower() in token_pool
                or posix_path.lower() in token_pool
                or filename in token_pool
                or filename.lower() in token_pool
                or stem in token_pool
                or stem.lower() in token_pool
                or stem_spaces in token_pool
                or stem_spaces.lower() in token_pool
            )

            if not is_referenced:
                msg = (
                    f"Asset '{rel_path}' ({asset.asset_type.value}, {asset.size_bytes} B) "
                    "has no static references found in parsed scripts."
                )
                sug = (
                    f"Verify if '{filename}' is loaded dynamically via Python or "
                    "consider removing it to reduce game package size."
                )
                issues.append(
                    self.create_issue(
                        message=msg,
                        location=Location(file_path=f"game/{rel_path}"),
                        suggestion=sug,
                        confidence=Confidence.SUSPECTED,
                        metadata={
                            "relative_path": rel_path,
                            "filename": filename,
                            "size_bytes": asset.size_bytes,
                            "asset_type": asset.asset_type.value,
                        },
                    )
                )

        return issues
