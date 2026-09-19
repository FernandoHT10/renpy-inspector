"""AST-based extraction of Ren'Py jump, call, and screen actions."""

import ast
from dataclasses import dataclass
from typing import Optional

from renpy_inspector.core.models.symbols import ReferenceKind


@dataclass(frozen=True)
class ExtractedAction:
    """An action reference extracted from Python AST."""

    category: str  # "jump", "call", "screen"
    target: str
    kind: ReferenceKind
    is_expression: bool
    is_screen: bool
    line_offset: int  # 0-indexed line offset within the parsed block/expression
    column_offset: int
    screen_action: Optional[str] = None


BARE_JUMP_FUNCTIONS = frozenset({"Jump", "Start"})
QUALIFIED_JUMP_FUNCTIONS = frozenset({"renpy.jump"})

BARE_CALL_FUNCTIONS = frozenset({"Call"})
QUALIFIED_CALL_FUNCTIONS = frozenset({"renpy.call", "renpy.call_in_new_context"})

SCREEN_ACTION_MAPPING = {
    "Show": "show",
    "Hide": "hide",
    "ShowTransient": "showtransient",
    "ToggleScreen": "togglescreen",
    "CallScreen": "callscreen",
    "ShowMenu": "showmenu",
    "renpy.show_screen": "show",
    "renpy.hide_screen": "hide",
    "renpy.call_screen": "call",
}

ACTION_PROPERTY_PREFIXES = (
    "action ",
    "hovered ",
    "unhovered ",
    "selected ",
    "alternate ",
    "clicked ",
)


def resolve_func_identifier(node_func: ast.AST) -> Optional[str]:
    """Resolve an AST call func node strictly to an allowed bare or renpy-qualified identifier.

    Calls on arbitrary objects (e.g. obj.Jump, player.Call) return None and are rejected.
    """
    if isinstance(node_func, ast.Name):
        return node_func.id
    if (
        isinstance(node_func, ast.Attribute)
        and isinstance(node_func.value, ast.Name)
        and node_func.value.id == "renpy"
    ):
        return f"renpy.{node_func.attr}"
    return None


def extract_actions_from_ast(
    code: str, mode: str = "exec"
) -> tuple[list[ExtractedAction], Optional[SyntaxError]]:
    """Parse code into Python AST and extract jump, call, and screen action calls.

    Returns:
        tuple of (extracted_actions_list, syntax_error_if_any)
    """
    actions: list[ExtractedAction] = []
    try:
        tree = ast.parse(code, mode=mode)
    except SyntaxError as e:
        return actions, e

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func_name = resolve_func_identifier(node.func)
        if not func_name:
            continue

        target: Optional[str] = None
        is_dynamic = False

        if func_name == "Start" and len(node.args) == 0:
            target = "start"
            is_dynamic = False
        elif len(node.args) > 0:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                target = first_arg.value.strip()
                is_dynamic = False
            else:
                is_dynamic = True
                try:
                    target = ast.unparse(first_arg).strip()
                except Exception:
                    target = "<expression>"
        else:
            continue

        if not target:
            continue

        kind = ReferenceKind.DYNAMIC if is_dynamic else ReferenceKind.STATIC
        is_expr = is_dynamic
        lineno = getattr(node, "lineno", 1) - 1
        col_offset = getattr(node, "col_offset", 0)

        if func_name in BARE_JUMP_FUNCTIONS or func_name in QUALIFIED_JUMP_FUNCTIONS:
            actions.append(
                ExtractedAction(
                    category="jump",
                    target=target,
                    kind=kind,
                    is_expression=is_expr,
                    is_screen=False,
                    line_offset=lineno,
                    column_offset=col_offset,
                )
            )
        elif func_name in BARE_CALL_FUNCTIONS or func_name in QUALIFIED_CALL_FUNCTIONS:
            actions.append(
                ExtractedAction(
                    category="call",
                    target=target,
                    kind=kind,
                    is_expression=is_expr,
                    is_screen=False,
                    line_offset=lineno,
                    column_offset=col_offset,
                )
            )
        elif func_name in SCREEN_ACTION_MAPPING:
            actions.append(
                ExtractedAction(
                    category="screen",
                    target=target,
                    kind=kind,
                    is_expression=is_expr,
                    is_screen=True,
                    line_offset=lineno,
                    column_offset=col_offset,
                    screen_action=SCREEN_ACTION_MAPPING[func_name],
                )
            )

    return actions, None


def calculate_delimiter_balance(text: str) -> int:
    """Calculate delimiter balance (+ for [({, - for ])}) properly ignoring quotes and escapes."""
    balance = 0
    in_quote: Optional[str] = None
    escaped = False

    for char in text:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if in_quote:
            if char == in_quote:
                in_quote = None
            continue
        if char in ('"', "'"):
            in_quote = char
            continue
        if char in "([{":
            balance += 1
        elif char in ")]}":
            balance -= 1

    return balance
