"""Rule detecting explicit image statements referencing nonexistent files."""

from pathlib import Path

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import AssetType, Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.rules.base import BaseRule


class MissingImageRule(BaseRule):
    """Detects missing image files in explicit image declarations."""

    rule_id = "RPY-IMAGE-001"
    title = "Missing Image File"
    category = Category.IMAGES
    default_severity = Severity.ERROR
    description = "Checks that explicit image statements point to existing image files."

    def analyze(self, context: ProjectContext) -> list[Issue]:
        issues: list[Issue] = []
        defined_image_names = {img.name for img in context.all_images}
        for img_asset in context.catalog.get_by_type(AssetType.IMAGE):
            stem = Path(img_asset.filename).stem
            defined_image_names.add(stem)
            defined_image_names.add(stem.replace("_", " "))

            # Index subdirectory slices (e.g. characters/musatobi/c1 -> musatobi c1)
            rel = Path(img_asset.relative_path)
            parts = list(rel.parts)
            parts[-1] = stem
            for i in range(len(parts)):
                sub_space = " ".join(parts[i:])
                defined_image_names.add(sub_space)
                defined_image_names.add(sub_space.replace("_", " "))
                sub_slash = "/".join(parts[i:])
                defined_image_names.add(sub_slash)
                defined_image_names.add(sub_slash.replace("_", " "))

        common_image_extensions = (".png", ".jpg", ".jpeg", ".webp", ".webm", ".ogv")

        for img in context.all_images:
            if img.is_dynamic or not img.asset_reference:
                continue

            ref = img.asset_reference.replace("\\", "/").strip("/")
            if not ref:
                continue

            # 1. Skip dynamic interpolation patterns like "[variant]"
            if "[" in ref and "]" in ref:
                continue

            # 2. Skip hex color Solid displayables (e.g. "#c00", "#0000cc88")
            if ref.startswith("#"):
                continue

            # 3. Check if file exists directly or in images/ subdirectory
            found = (
                context.catalog.find_exact(ref)
                or context.catalog.find_exact(f"images/{ref}")
                or context.catalog.find_case_insensitive(ref)
                or context.catalog.find_case_insensitive(f"images/{ref}")
            )

            # 4. If extension was omitted, try standard image extensions
            if not found and not Path(ref).suffix:
                for ext in common_image_extensions:
                    found = (
                        context.catalog.find_exact(f"{ref}{ext}")
                        or context.catalog.find_exact(f"images/{ref}{ext}")
                        or context.catalog.find_case_insensitive(f"{ref}{ext}")
                        or context.catalog.find_case_insensitive(f"images/{ref}{ext}")
                    )
                    if found:
                        break

            # 5. Check if it's an alias to another defined image tag
            if not found and ref in defined_image_names:
                continue

            if not found:
                msg = (
                    f"Image file '{img.asset_reference}' referenced by "
                    f"image '{img.name}' does not exist on disk."
                )
                sug = f"Add '{img.asset_reference}' to 'game/images/' or update path."
                meta = {"image_name": img.name, "asset_reference": img.asset_reference}

                issues.append(
                    self.create_issue(
                        message=msg,
                        location=img.location,
                        suggestion=sug,
                        metadata=meta,
                    )
                )

        return issues
