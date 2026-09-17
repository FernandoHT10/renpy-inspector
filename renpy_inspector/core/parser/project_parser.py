"""Orchestrates parsing of all script files within a Ren'Py project."""

from pathlib import Path
from typing import Callable, Optional, Sequence, Union

from renpy_inspector.core.models.enums import AssetType
from renpy_inspector.core.parser.result import ParsedProject
from renpy_inspector.core.parser.rpy_parser import RpyParser
from renpy_inspector.core.scanner.asset_catalog import AssetCatalog
from renpy_inspector.core.scanner.file_scanner import FileScanner


class ProjectParser:
    """Coordinates parsing across all .rpy/.rpym files in a Ren'Py project."""

    def __init__(self, parser: Optional[RpyParser] = None) -> None:
        self.parser = parser or RpyParser()

    def parse_project(
        self,
        game_directory: Union[str, Path],
        catalog: Optional[AssetCatalog] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> ParsedProject:
        """Parse all script files (.rpy and .rpym) in the game directory.

        Args:
            game_directory: Absolute or relative path to the 'game/' directory.
            catalog: Optional pre-scanned AssetCatalog. If not provided, a FileScanner runs first.
            progress_callback: Optional callback receiving (rel_path, current_index, total_count).

        Returns:
            ParsedProject containing all parsed file results and aggregated metrics.
        """
        game_path = Path(game_directory).resolve()
        parsed_project = ParsedProject()

        if catalog is None:
            scanner = FileScanner()
            catalog = scanner.scan(game_path)

        # Filter strictly for scripts (.rpy, .rpym), explicitly excluding .rpyc
        script_assets = [
            asset for asset in catalog.get_by_type(AssetType.SCRIPT)
            if not asset.extension.endswith("c")
        ]

        total_scripts = len(script_assets)

        for idx, asset in enumerate(script_assets, start=1):
            rel_path = asset.relative_path
            abs_path = asset.absolute_path

            if progress_callback:
                progress_callback(rel_path, idx, total_scripts)

            try:
                file_result = self.parser.parse_file(
                    file_path=abs_path,
                    display_path=rel_path,
                )
                parsed_project.files[rel_path] = file_result
            except Exception:
                parsed_project.failed_files.append(rel_path)

        return parsed_project

    def parse_files(
        self,
        file_paths: Sequence[Path],
        game_directory: Path,
    ) -> ParsedProject:
        """Parse a specific list of script file paths."""
        parsed_project = ParsedProject()
        resolved_game = game_directory.resolve()

        for path in file_paths:
            if path.suffix.lower() not in (".rpy", ".rpym"):
                continue

            try:
                rel_path = path.resolve().relative_to(resolved_game).as_posix()
            except ValueError:
                rel_path = path.name

            try:
                file_result = self.parser.parse_file(
                    file_path=path,
                    display_path=rel_path,
                )
                parsed_project.files[rel_path] = file_result
            except Exception:
                parsed_project.failed_files.append(rel_path)

        return parsed_project
