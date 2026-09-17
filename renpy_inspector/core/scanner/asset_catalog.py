"""Asset catalog for storing, querying, and case-sensitivity validation of project assets."""

from collections import defaultdict
from typing import Optional, Sequence

from renpy_inspector.core.models.asset import AssetInfo
from renpy_inspector.core.models.enums import AssetType


def normalize_rel_path(path_str: str) -> str:
    """Normalize relative path to use POSIX forward slashes and strip leading slashes."""
    return path_str.replace("\\", "/").strip("/")


class AssetCatalog:
    """In-memory catalog of all discovered assets with case-sensitivity awareness."""

    def __init__(self, assets: Optional[Sequence[AssetInfo]] = None) -> None:
        self._assets_by_exact_path: dict[str, AssetInfo] = {}
        self._assets_by_folded_path: dict[str, list[AssetInfo]] = defaultdict(list)
        self._assets_by_type: dict[AssetType, list[AssetInfo]] = defaultdict(list)

        if assets:
            for asset in assets:
                self.add_asset(asset)

    def add_asset(self, asset: AssetInfo) -> None:
        """Add an asset to the catalog, updating exact, case-folded, and typed indices."""
        normalized = normalize_rel_path(asset.relative_path)
        self._assets_by_exact_path[normalized] = asset
        self._assets_by_folded_path[normalized.lower()].append(asset)
        self._assets_by_type[asset.asset_type].append(asset)

    def find_exact(self, rel_path: str) -> Optional[AssetInfo]:
        """Find an asset matching the exact case of the given relative path."""
        normalized = normalize_rel_path(rel_path)
        return self._assets_by_exact_path.get(normalized)

    def find_case_insensitive(self, rel_path: str) -> list[AssetInfo]:
        """Find assets matching the given relative path ignoring case."""
        normalized_lower = normalize_rel_path(rel_path).lower()
        return list(self._assets_by_folded_path.get(normalized_lower, []))

    def has_case_mismatch(self, rel_path: str) -> Optional[str]:
        """Check if a reference exists on disk with different casing.

        Returns:
            The exact disk path if a case-mismatch exists.
            None if the reference matches exactly, or if the file does not exist at all.
        """
        normalized = normalize_rel_path(rel_path)
        # If exact match exists, there is NO mismatch
        if normalized in self._assets_by_exact_path:
            return None

        # Check if case-folded match exists
        matches = self._assets_by_folded_path.get(normalized.lower())
        if matches:
            # Return the first matching real disk relative path
            return matches[0].relative_path

        return None

    def get_by_type(self, asset_type: AssetType) -> list[AssetInfo]:
        """Return all assets belonging to a specific AssetType."""
        return list(self._assets_by_type.get(asset_type, []))

    def all_assets(self) -> list[AssetInfo]:
        """Return a list of all indexed assets."""
        return list(self._assets_by_exact_path.values())

    def count_by_type(self) -> dict[AssetType, int]:
        """Return count breakdown by AssetType."""
        return {
            asset_type: len(self._assets_by_type.get(asset_type, []))
            for asset_type in AssetType
        }

    def total_count(self) -> int:
        """Return total number of assets indexed."""
        return len(self._assets_by_exact_path)

    def __len__(self) -> int:
        return self.total_count()

    def __contains__(self, rel_path: str) -> bool:
        return normalize_rel_path(rel_path) in self._assets_by_exact_path
