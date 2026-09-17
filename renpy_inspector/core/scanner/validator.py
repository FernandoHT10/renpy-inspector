"""Validator to determine if a directory is a valid Ren'Py project."""

import os
from pathlib import Path
from typing import Union

from renpy_inspector.core.models.project import ValidationResult

# Well-known markers typically found in Ren'Py projects
TYPICAL_SCRIPT_MARKERS = ("options.rpy", "script.rpy", "screens.rpy", "gui.rpy")
TYPICAL_ROOT_MARKERS = ("renpy.py", "renpy.sh", "renpy.exe", "log.txt", "errors.txt")


class ProjectValidator:
    """Validates whether a filesystem path corresponds to a genuine Ren'Py project."""

    @classmethod
    def validate(cls, path_input: Union[str, Path]) -> ValidationResult:
        """Inspect the directory and return a structured ValidationResult."""
        target_path = Path(path_input).resolve()

        if not target_path.exists():
            return ValidationResult(
                is_valid=False,
                root_path=target_path,
                errors=(f"Path does not exist: {target_path}",),
            )

        if not target_path.is_dir():
            return ValidationResult(
                is_valid=False,
                root_path=target_path,
                errors=(f"Path is not a directory: {target_path}",),
            )

        # Determine root_path and game_path
        if target_path.name.lower() == "game" and target_path.is_dir():
            game_path = target_path
            root_path = target_path.parent
        else:
            game_path = target_path / "game"
            root_path = target_path

        if not game_path.is_dir():
            return ValidationResult(
                is_valid=False,
                root_path=root_path,
                errors=(
                    f"Ren'Py 'game/' directory not found in '{root_path}'. "
                    "A valid Ren'Py project must contain a 'game/' folder.",
                ),
            )

        # Inspect game directory for markers and scripts
        detected_markers: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []
        has_scripts = False

        try:
            for entry in os.scandir(game_path):
                name_lower = entry.name.lower()
                if entry.is_file():
                    if name_lower.endswith((".rpy", ".rpyc", ".rpym")):
                        has_scripts = True
                    if name_lower in TYPICAL_SCRIPT_MARKERS:
                        detected_markers.append(entry.name)
                elif entry.is_dir():
                    if name_lower in ("tl", "images", "audio", "gui", "fonts"):
                        detected_markers.append(f"{entry.name}/")
        except OSError as exc:
            return ValidationResult(
                is_valid=False,
                root_path=root_path,
                game_path=game_path,
                errors=(f"Failed to read 'game/' directory: {exc}",),
            )

        # If no scripts were found directly in game/, check subdirectories recursively for scripts
        if not has_scripts:
            has_scripts = cls._has_any_script(game_path)

        if not has_scripts:
            errors.append(
                f"Directory '{game_path}' contains no Ren'Py script files (.rpy or .rpyc)."
            )
            return ValidationResult(
                is_valid=False,
                root_path=root_path,
                game_path=game_path,
                detected_markers=tuple(detected_markers),
                warnings=tuple(warnings),
                errors=tuple(errors),
            )

        # Check for root markers
        try:
            for entry in os.scandir(root_path):
                if entry.name.lower() in TYPICAL_ROOT_MARKERS:
                    detected_markers.append(entry.name)
        except OSError:
            pass

        # Optional checks for common files (non-blocking warnings)
        if "options.rpy" not in [m.lower() for m in detected_markers]:
            warnings.append("No 'options.rpy' detected in game/ folder.")
        if "script.rpy" not in [m.lower() for m in detected_markers]:
            warnings.append(
                "No 'script.rpy' detected in game/ folder (scripts may be organized in subfolders)."
            )

        return ValidationResult(
            is_valid=True,
            root_path=root_path,
            game_path=game_path,
            detected_markers=tuple(sorted(detected_markers)),
            warnings=tuple(warnings),
            errors=(),
        )

    @classmethod
    def _has_any_script(cls, directory: Path) -> bool:
        """Recursively check if there are any .rpy or .rpyc files in the directory."""
        try:
            for root, _, files in os.walk(directory):
                for f in files:
                    if f.lower().endswith((".rpy", ".rpyc", ".rpym")):
                        return True
        except OSError:
            pass
        return False
