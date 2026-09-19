"""Fast, safe filesystem scanner for discovering Ren'Py scripts, images, audio, and fonts."""

import os
from pathlib import Path
from typing import Callable, Optional, Set

from renpy_inspector.core.models.asset import AssetInfo
from renpy_inspector.core.models.enums import AssetType
from renpy_inspector.core.models.failures import ScanError
from renpy_inspector.core.scanner.asset_catalog import AssetCatalog

# Extension sets mapped to AssetType (based on official Ren'Py documentation)
SCRIPT_EXTENSIONS = {".rpy", ".rpym"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".svg", ".bmp", ".gif"}
AUDIO_EXTENSIONS = {".ogg", ".mp3", ".wav", ".opus", ".flac", ".mp2"}
FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2", ".ttc"}
VIDEO_EXTENSIONS = {".webm", ".ogv", ".mp4", ".mkv", ".avi"}

EXTENSION_MAP: dict[str, AssetType] = {}
for ext in SCRIPT_EXTENSIONS:
    EXTENSION_MAP[ext] = AssetType.SCRIPT
for ext in IMAGE_EXTENSIONS:
    EXTENSION_MAP[ext] = AssetType.IMAGE
for ext in AUDIO_EXTENSIONS:
    EXTENSION_MAP[ext] = AssetType.AUDIO
for ext in FONT_EXTENSIONS:
    EXTENSION_MAP[ext] = AssetType.FONT
for ext in VIDEO_EXTENSIONS:
    EXTENSION_MAP[ext] = AssetType.VIDEO

# Directories to skip by default (Ren'Py cache, version control, IDE metadata)
IGNORED_DIRS: Set[str] = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    ".vscode",
    ".idea",
    "cache",  # Ren'Py persistent cache inside game/cache
}


class FileScanner:
    """Recursively scans a Ren'Py game directory using os.scandir without loading file contents."""

    def __init__(
        self,
        ignored_dirs: Optional[Set[str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.ignored_dirs = set(ignored_dirs) if ignored_dirs is not None else IGNORED_DIRS
        self.progress_callback = progress_callback

    def scan(
        self,
        game_directory: Path,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> AssetCatalog:
        """Scan the game directory and populate an AssetCatalog with discovered assets.

        Args:
            game_directory: Absolute Path to the 'game/' folder of the project.
            is_cancelled: Optional callback returning True if scan should abort.

        Returns:
            An AssetCatalog containing all categorized assets.
        """
        resolved_game_dir = game_directory.resolve()
        catalog = AssetCatalog()

        if not resolved_game_dir.is_dir():
            return catalog

        # Stack-based traversal using os.scandir for optimal speed and recursion safety
        dir_stack = [resolved_game_dir]

        while dir_stack:
            if is_cancelled and is_cancelled():
                break

            current_dir = dir_stack.pop()

            try:
                with os.scandir(current_dir) as entries:
                    entry_list = list(entries)
                    rpy_stems = {
                        e.name[:-4].lower()
                        for e in entry_list
                        if e.is_file(follow_symlinks=False) and e.name.lower().endswith(".rpy")
                    }

                    for entry in entry_list:
                        if is_cancelled and is_cancelled():
                            break

                        try:
                            if entry.is_dir(follow_symlinks=False):
                                if entry.name.lower() not in self.ignored_dirs:
                                    dir_stack.append(Path(entry.path))
                            elif entry.is_file(follow_symlinks=False):
                                ext = Path(entry.name).suffix.lower()
                                lower_name = entry.name.lower()

                                if lower_name.endswith(".rpyc"):
                                    catalog.compiled_scripts_count += 1

                                if lower_name.endswith("_ren.py"):
                                    asset_type = AssetType.SCRIPT
                                    ext = "_ren.py"
                                else:
                                    # Skip .rpym if corresponding .rpy exists in same directory
                                    if ext == ".rpym" and entry.name[:-5].lower() in rpy_stems:
                                        continue
                                    asset_type = EXTENSION_MAP.get(ext)

                                if asset_type is not None:
                                    entry_path = Path(entry.path)
                                    rel_path = entry_path.relative_to(resolved_game_dir).as_posix()
                                    stat_info = entry.stat()

                                    asset = AssetInfo(
                                        relative_path=rel_path,
                                        absolute_path=entry_path,
                                        asset_type=asset_type,
                                        filename=entry.name,
                                        extension=ext,
                                        size_bytes=stat_info.st_size,
                                    )
                                    catalog.add_asset(asset)

                                    if self.progress_callback:
                                        self.progress_callback(rel_path)
                        except (KeyboardInterrupt, SystemExit):
                            raise
                        except (OSError, PermissionError) as exc:
                            is_d = False
                            try:
                                is_d = entry.is_dir(follow_symlinks=False)
                            except Exception:
                                pass
                            catalog.scan_errors.append(
                                ScanError(
                                    path=str(entry.path),
                                    operation="stat",
                                    error_type=type(exc).__name__,
                                    error_message=str(exc),
                                    is_directory=is_d,
                                )
                            )
            except (KeyboardInterrupt, SystemExit):
                raise
            except (OSError, PermissionError) as exc:
                catalog.scan_errors.append(
                    ScanError(
                        path=str(current_dir),
                        operation="scandir",
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                        is_directory=True,
                    )
                )

        return catalog
