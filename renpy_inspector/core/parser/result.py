"""Result models aggregating parsed symbols and project-wide statistics."""

from dataclasses import dataclass, field
from typing import Any

from renpy_inspector.core.models.symbols import (
    AudioReference,
    CallReference,
    DialogueLine,
    ImageDefinition,
    JumpReference,
    LabelSymbol,
    MenuBlock,
    PythonBlock,
    ReferenceKind,
    ScreenDefinition,
    TranslateBlock,
    UnreachableStatement,
    VariableDeclaration,
)
from renpy_inspector.core.parser.errors import ParseError


@dataclass
class FileParseResult:
    """Holds all symbols and errors extracted from a single script file."""

    file_path: str
    labels: list[LabelSymbol] = field(default_factory=list)
    jumps: list[JumpReference] = field(default_factory=list)
    calls: list[CallReference] = field(default_factory=list)
    images: list[ImageDefinition] = field(default_factory=list)
    audios: list[AudioReference] = field(default_factory=list)
    variables: list[VariableDeclaration] = field(default_factory=list)
    translations: list[TranslateBlock] = field(default_factory=list)
    python_blocks: list[PythonBlock] = field(default_factory=list)
    screens: list[ScreenDefinition] = field(default_factory=list)
    menus: list[MenuBlock] = field(default_factory=list)
    dialogues: list[DialogueLine] = field(default_factory=list)
    unreachables: list[UnreachableStatement] = field(default_factory=list)
    scenes_and_shows: list[str] = field(default_factory=list)
    registered_channels: list[str] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)


    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def defines(self) -> list[VariableDeclaration]:
        return [v for v in self.variables if v.kind == "define"]

    @property
    def defaults(self) -> list[VariableDeclaration]:
        return [v for v in self.variables if v.kind == "default"]

    @property
    def dynamic_references_count(self) -> int:
        dynamic_jumps = sum(1 for j in self.jumps if j.kind == ReferenceKind.DYNAMIC)
        dynamic_calls = sum(1 for c in self.calls if c.kind == ReferenceKind.DYNAMIC)
        dynamic_audios = sum(1 for a in self.audios if a.kind == ReferenceKind.DYNAMIC)
        dynamic_images = sum(1 for img in self.images if img.is_dynamic)
        return dynamic_jumps + dynamic_calls + dynamic_audios + dynamic_images

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "labels": [s.to_dict() for s in self.labels],
            "jumps": [s.to_dict() for s in self.jumps],
            "calls": [s.to_dict() for s in self.calls],
            "images": [s.to_dict() for s in self.images],
            "audios": [s.to_dict() for s in self.audios],
            "variables": [s.to_dict() for s in self.variables],
            "translations": [s.to_dict() for s in self.translations],
            "python_blocks": [s.to_dict() for s in self.python_blocks],
            "screens": [s.to_dict() for s in self.screens],
            "menus": [s.to_dict() for s in self.menus],
            "dialogues": [s.to_dict() for s in self.dialogues],
            "unreachables": [s.to_dict() for s in self.unreachables],
            "errors": [s.to_dict() for s in self.errors],
        }


@dataclass
class ParsedProject:
    """Aggregated symbols and statistics across all parsed script files."""

    files: dict[str, FileParseResult] = field(default_factory=dict)
    failed_files: list[str] = field(default_factory=list)

    @property
    def total_files_parsed(self) -> int:
        return len(self.files)

    @property
    def total_files_failed(self) -> int:
        return len(self.failed_files)

    @property
    def total_labels(self) -> int:
        return sum(len(f.labels) for f in self.files.values())

    @property
    def total_jumps(self) -> int:
        return sum(len(f.jumps) for f in self.files.values())

    @property
    def total_calls(self) -> int:
        return sum(len(f.calls) for f in self.files.values())

    @property
    def total_screens(self) -> int:
        return sum(len(f.screens) for f in self.files.values())

    @property
    def total_images(self) -> int:
        return sum(len(f.images) for f in self.files.values())

    @property
    def total_audios(self) -> int:
        return sum(len(f.audios) for f in self.files.values())

    @property
    def total_defines(self) -> int:
        return sum(len(f.defines) for f in self.files.values())

    @property
    def total_defaults(self) -> int:
        return sum(len(f.defaults) for f in self.files.values())

    @property
    def total_translations(self) -> int:
        return sum(len(f.translations) for f in self.files.values())

    @property
    def total_python_blocks(self) -> int:
        return sum(len(f.python_blocks) for f in self.files.values())

    @property
    def total_dynamic_references(self) -> int:
        return sum(f.dynamic_references_count for f in self.files.values())

    def summary_stats(self) -> dict[str, int]:
        """Return comprehensive metric statistics for CLI and reporting."""
        return {
            "Files parsed": self.total_files_parsed,
            "Files failed": self.total_files_failed,
            "Labels found": self.total_labels,
            "Jumps found": self.total_jumps,
            "Calls found": self.total_calls,
            "Images found": self.total_images,
            "Audio references found": self.total_audios,
            "Defines found": self.total_defines,
            "Defaults found": self.total_defaults,
            "Translations found": self.total_translations,
            "Python blocks found": self.total_python_blocks,
            "Dynamic references found": self.total_dynamic_references,
        }
