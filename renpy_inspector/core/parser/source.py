"""Safe file loading with robust Unicode and encoding detection."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union


@dataclass(frozen=True)
class SourceFile:
    """Represents the loaded textual content of a Ren'Py script file."""

    file_path: str  # Relative path (e.g. "game/script.rpy")
    lines: tuple[str, ...]
    content: str
    encoding: str
    encoding_warning: Optional[str] = None


class SourceLoader:
    """Loads script source text without executing any code or binary evaluation."""

    @classmethod
    def load(cls, file_path: Union[str, Path], display_path: Optional[str] = None) -> SourceFile:
        """Safely read script content trying UTF-8, UTF-8-SIG, and fallback replace."""
        path = Path(file_path).resolve()
        disp_path = display_path or str(path)

        # 1. Try UTF-8 (with automatic BOM stripping via utf-8-sig)
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                content = f.read()
                if content.startswith("\ufeff"):
                    content = content.removeprefix("\ufeff")
                lines = tuple(content.splitlines())
                return SourceFile(
                    file_path=disp_path,
                    lines=lines,
                    content=content,
                    encoding="utf-8",
                )
        except UnicodeDecodeError:
            pass

        # 2. Fallback: UTF-8 with replacement characters so parsing can proceed safely
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            if content.startswith("\ufeff"):
                content = content.removeprefix("\ufeff")
            lines = tuple(content.splitlines())
            return SourceFile(
                file_path=disp_path,
                lines=lines,
                content=content,
                encoding="utf-8 (corrupt bytes replaced)",
                encoding_warning="File contains invalid UTF-8 bytes that were replaced.",
            )
