"""Models representing AST symbols (labels, jumps, calls, images, audio, variables)."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from renpy_inspector.core.models.location import Location
from renpy_inspector.core.models.resolution import parse_audio_target


class ReferenceKind(str, Enum):
    """Indicates whether a code reference is statically resolvable or dynamic."""

    STATIC = "STATIC"
    DYNAMIC = "DYNAMIC"


@dataclass(frozen=True)
class LabelSymbol:
    """Represents a defined Ren'Py label."""

    name: str
    location: Location
    is_local: bool = False
    parent_label: Optional[str] = None
    params: Optional[str] = None
    is_menu: bool = False

    @property
    def full_name(self) -> str:
        """Return the fully qualified name (e.g. 'chapter1.choice_a')."""
        if self.is_local and self.parent_label:
            return f"{self.parent_label}{self.name}"
        return self.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "location": self.location.to_dict(),
            "is_local": self.is_local,
            "parent_label": self.parent_label,
            "params": self.params,
            "is_menu": self.is_menu,
        }


@dataclass(frozen=True)
class JumpReference:
    """Represents a jump statement in script."""

    target: str
    location: Location
    is_expression: bool = False
    kind: ReferenceKind = ReferenceKind.STATIC
    scope_label: Optional[str] = None

    def __post_init__(self) -> None:
        # Sync is_expression with kind if either was set specifically
        if self.is_expression and self.kind == ReferenceKind.STATIC:
            object.__setattr__(self, "kind", ReferenceKind.DYNAMIC)
        elif self.kind == ReferenceKind.DYNAMIC and not self.is_expression:
            object.__setattr__(self, "is_expression", True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "location": self.location.to_dict(),
            "is_expression": self.is_expression,
            "kind": self.kind.value,
            "scope_label": self.scope_label,
        }


@dataclass(frozen=True)
class CallReference:
    """Represents a call statement in script."""

    target: str
    location: Location
    is_expression: bool = False
    kind: ReferenceKind = ReferenceKind.STATIC
    is_screen: bool = False
    screen_action: Optional[str] = None
    scope_label: Optional[str] = None

    def __post_init__(self) -> None:
        if self.is_expression and self.kind == ReferenceKind.STATIC:
            object.__setattr__(self, "kind", ReferenceKind.DYNAMIC)
        elif self.kind == ReferenceKind.DYNAMIC and not self.is_expression:
            object.__setattr__(self, "is_expression", True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "location": self.location.to_dict(),
            "is_expression": self.is_expression,
            "kind": self.kind.value,
            "is_screen": self.is_screen,
            "screen_action": self.screen_action,
            "scope_label": self.scope_label,
        }


@dataclass(frozen=True)
class ImageDefinition:
    """Represents an image statement declaration."""

    name: str  # e.g. "eileen happy" or "bg room"
    location: Location
    asset_reference: Optional[str] = None  # e.g. "images/room.png" if explicit static file
    is_dynamic: bool = False

    def __init__(
        self,
        name: Optional[str] = None,
        location: Optional[Location] = None,
        asset_reference: Optional[str] = None,
        is_dynamic: bool = False,
        tag: Optional[str] = None,
        attributes: tuple[str, ...] = (),
        explicit_file: Optional[str] = None,
    ) -> None:
        computed_name = name
        if computed_name is None:
            if tag:
                computed_name = f"{tag} {' '.join(attributes)}".strip()
            else:
                computed_name = ""

        ref = asset_reference if asset_reference is not None else explicit_file

        object.__setattr__(self, "name", computed_name)
        object.__setattr__(self, "location", location)
        object.__setattr__(self, "asset_reference", ref)
        object.__setattr__(self, "is_dynamic", is_dynamic)

    @property
    def tag(self) -> str:
        """First token of the image name (e.g. 'eileen' in 'eileen happy')."""
        return self.name.split()[0] if self.name else ""

    @property
    def attributes(self) -> tuple[str, ...]:
        """Additional tokens following tag."""
        parts = self.name.split()
        return tuple(parts[1:]) if len(parts) > 1 else ()

    @property
    def full_tag(self) -> str:
        """Return the combined image name."""
        return self.name

    @property
    def explicit_file(self) -> Optional[str]:
        """Backward compatibility alias for asset_reference."""
        return self.asset_reference

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tag": self.tag,
            "attributes": list(self.attributes),
            "full_tag": self.full_tag,
            "location": self.location.to_dict(),
            "asset_reference": self.asset_reference,
            "explicit_file": self.asset_reference,
            "is_dynamic": self.is_dynamic,
        }


# Backward-compatibility alias
ImageSymbol = ImageDefinition


@dataclass(frozen=True)
class AudioReference:
    """Represents a play or queue audio statement."""

    channel: str  # e.g. "music", "sound", "voice", "audio"
    target: str  # e.g. "audio/theme.ogg" or identifier "theme_song"
    location: Location
    action: str = "play"  # "play" or "queue"
    kind: ReferenceKind = ReferenceKind.STATIC
    is_quoted: bool = True
    clauses: tuple[str, ...] = ()
    clean_target: str = ""

    def __post_init__(self) -> None:
        if not self.clean_target:
            parsed_clauses, cleaned, _ = parse_audio_target(self.target)
            object.__setattr__(self, "clean_target", cleaned)
            if not self.clauses:
                object.__setattr__(self, "clauses", parsed_clauses)

    @property
    def is_dynamic(self) -> bool:
        return self.kind == ReferenceKind.DYNAMIC

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "target": self.target,
            "clean_target": self.clean_target,
            "is_quoted": self.is_quoted,
            "clauses": list(self.clauses),
            "location": self.location.to_dict(),
            "action": self.action,
            "kind": self.kind.value,
            "is_dynamic": self.is_dynamic,
        }


@dataclass(frozen=True)
class VariableDeclaration:
    """Represents a define or default statement."""

    name: str  # e.g. "score", "config.name"
    kind: str  # "define" or "default"
    location: Location
    raw_value: str = ""
    priority: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "location": self.location.to_dict(),
            "raw_value": self.raw_value,
            "priority": self.priority,
        }


@dataclass(frozen=True)
class TranslateBlock:
    """Represents a translate block declaration."""

    language: str  # e.g. "spanish", "None"
    identifier: str  # e.g. "start_915cb944" or "strings"
    location: Location

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "identifier": self.identifier,
            "location": self.location.to_dict(),
        }


@dataclass(frozen=True)
class PythonBlock:
    """Represents an embedded Python block (tracked without executing)."""

    block_type: str  # e.g. "python", "init python", "python early"
    location: Location
    end_line: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_type": self.block_type,
            "location": self.location.to_dict(),
            "end_line": self.end_line,
        }


@dataclass(frozen=True)
class ScreenDefinition:
    """Represents a screen statement declaration."""

    name: str
    location: Location
    params: Optional[str] = None
    variant: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "location": self.location.to_dict(),
            "params": self.params,
            "variant": self.variant,
        }


@dataclass(frozen=True)
class MenuBlock:
    """Represents a Ren'Py menu: block statement."""

    location: Location
    item_count: int = 0
    scope_label: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": self.location.to_dict(),
            "item_count": self.item_count,
            "scope_label": self.scope_label,
        }


@dataclass(frozen=True)
class DialogueLine:
    """Represents a dialogue text line or say statement."""

    text: str
    location: Location
    speaker: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "location": self.location.to_dict(),
            "speaker": self.speaker,
        }


@dataclass(frozen=True)
class UnreachableStatement:
    """Represents a statement directly following an unconditional jump or return."""

    statement: str
    location: Location
    preceding_statement: str
    preceding_line: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement": self.statement,
            "location": self.location.to_dict(),
            "preceding_statement": self.preceding_statement,
            "preceding_line": self.preceding_line,
        }


@dataclass(frozen=True)
class InitStatement:
    """Represents an init statement or block with an explicit priority."""

    priority: int
    statement_type: str  # "init", "init python", "init offset"
    location: Location

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority,
            "statement_type": self.statement_type,
            "location": self.location.to_dict(),
        }



