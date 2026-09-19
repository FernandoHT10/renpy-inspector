"""Deterministic static parser for Ren'Py scripts (.rpy and .rpym)."""

import re
import textwrap
from dataclasses import replace
from pathlib import Path
from typing import Any, Optional, Union

from renpy_inspector.core.models.enums import Severity
from renpy_inspector.core.models.location import Location
from renpy_inspector.core.models.resolution import parse_audio_target
from renpy_inspector.core.models.symbols import (
    AudioReference,
    CallReference,
    DialogueLine,
    ImageDefinition,
    InitStatement,
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
from renpy_inspector.core.parser.action_extractor import (
    ACTION_PROPERTY_PREFIXES,
    ExtractedAction,
    calculate_delimiter_balance,
    extract_actions_from_ast,
)
from renpy_inspector.core.parser.errors import ParseError
from renpy_inspector.core.parser.lexer import LogicalLine, ScriptLexer
from renpy_inspector.core.parser.result import FileParseResult
from renpy_inspector.core.parser.source import SourceFile, SourceLoader

# Regex patterns for Ren'Py statements (using Unicode-aware word matching)
RE_LABEL = re.compile(r"^label\s+([\w\.]+)(?:\s*\((.*)\))?\s*:$", re.UNICODE)
RE_MENU = re.compile(r"^menu\s+([\w\.]+)(?:\s*\((.*)\))?\s*:$", re.UNICODE)
RE_MENU_ITEM = re.compile(
    r'^(?:"((?:\\.|[^"\\])+)"|\'((?:\\.|[^\'\\])+)\')(?:\s*\(.*?\))?(?:\s+if\s+.*)?\s*:$',
    re.UNICODE,
)
RE_SCREEN = re.compile(r"^screen\s+([\w\.]+)(?:\s*\((.*)\))?.*:$", re.UNICODE)
RE_VARIANT_STMT = re.compile(r'^variant\s+["\'](\w+)["\']', re.UNICODE)
RE_VARIANT_HEADER = re.compile(r'variant\s*=\s*["\'](\w+)["\']', re.UNICODE)
RE_QUOTED_STRING = re.compile(
    r'"((?:\\.|[^"\\])*)"|\'((?:\\.|[^\'\\])*)\'', re.UNICODE
)
RE_JUMP = re.compile(r"^jump\s+(.+)$", re.UNICODE)
RE_CALL = re.compile(r"^call\s+(.+)$", re.UNICODE)
RE_IMAGE_EQUAL = re.compile(r"^image\s+([^=]+)=\s*(.+)$", re.UNICODE)
RE_IMAGE_ATL = re.compile(r"^image\s+([^:]+):$", re.UNICODE)
RE_LAYEREDIMAGE = re.compile(r"^layeredimage\s+([^:]+):$", re.UNICODE)
RE_AUDIO_QUOTED = re.compile(
    r"^(play|queue)\s+([\w]+)\s+(\"[^\"]*\"|'[^']*')(.*)$", re.UNICODE
)
RE_AUDIO_LIST = re.compile(
    r"^(play|queue)\s+([\w]+)\s+\[([^\]]+)\](.*)$", re.UNICODE
)
RE_QUOTED_ITEM = re.compile(r"(\"[^\"]*\"|'[^']*')", re.UNICODE)
RE_AUDIO_DYNAMIC = re.compile(
    r"^(play|queue)\s+([\w]+)\s+([\w\.]+)(.*)$", re.UNICODE
)
RE_VOICE_QUOTED = re.compile(
    r"^voice\s+(\"[^\"]*\"|'[^']*')(.*)$", re.UNICODE
)
RE_VOICE_DYNAMIC = re.compile(
    r"^voice\s+([\w\.]+)(.*)$", re.UNICODE
)
RE_AUDIO_CLAUSE = re.compile(r"^(<[^>]+>\s*)+")
RE_DEFINE_DEFAULT = re.compile(
    r"^(define|default)(\s+-?\d+)?\s+([\w\.]+)\s*=\s*(.*)$", re.UNICODE
)
RE_TRANSLATE = re.compile(r"^translate\s+([\w]+)\s+([^:]+):$", re.UNICODE)
RE_PYTHON_BLOCK = re.compile(
    r"^(?:init(?:\s+-?\d+)?\s+)?python(?:\s+(?:early|hide))?(?:\s+in\s+[\w\.]+)?\s*:$",
    re.UNICODE,
)
RE_INIT_STMT = re.compile(
    r"^init(?:\s+(-?\d+))?(?:\s+python(?:\s+(?:early|hide))?(?:\s+in\s+[\w\.]+)*)?\s*:$",
    re.UNICODE,
)
RE_INIT_OFFSET = re.compile(r"^init\s+offset\s*=\s*(-?\d+)", re.UNICODE)
RE_SCENE_SHOW = re.compile(r"^(scene|show)\s+([^:\n\r]+)", re.UNICODE)
RE_SHOW_SCREEN = re.compile(r"^(show|hide)\s+screen\s+([\w\.]+)(.*)$", re.UNICODE)
RE_REGISTER_CHANNEL = re.compile(r"register_channel\s*\(\s*[\"']([\w]+)[\"']", re.UNICODE)
RE_CUSTOM_TEXT_TAG = re.compile(
    r"(?:renpy\.)?config\.custom_text_tags\s*\[\s*['\"]([\w]+)['\"]\s*\]",
    re.UNICODE,
)
RE_SELF_CLOSING_TEXT_TAG = re.compile(
    r"(?:renpy\.)?config\.self_closing_custom_text_tags\s*\[\s*['\"]([\w]+)['\"]\s*\]",
    re.UNICODE,
)
RE_ACTION_JUMP = re.compile(
    r"\b(?:Jump|renpy\.jump)\s*\(\s*['\"]([\w\.]+)['\"]\s*\)", re.UNICODE
)
RE_ACTION_CALL = re.compile(
    r"\b(?:Call|renpy\.call|renpy\.call_in_new_context)\s*\(\s*['\"]([\w\.]+)['\"]\s*\)",
    re.UNICODE,
)
RE_ACTION_START = re.compile(
    r"\bStart\s*\(\s*['\"]([\w\.]+)['\"]\s*\)", re.UNICODE
)
RE_ACTION_SCREEN = re.compile(
    r"\b(Show|Hide|ToggleScreen|ShowTransient|CallScreen|renpy\.show_screen|renpy\.hide_screen)\s*\(\s*['\"]([\w\.]+)['\"]\s*\)",
    re.UNICODE,
)


def unquote_string(text: str) -> Optional[str]:
    """Extract string content from quotes if enclosed in single or double quotes."""
    s = text.strip()
    if len(s) >= 2 and (
        (s.startswith('"') and s.endswith('"'))
        or (s.startswith("'") and s.endswith("'"))
    ):
        return s[1:-1]
    return None


class RpyParser:
    """Parses Ren'Py script files into structured symbols without executing any code."""

    def __init__(self) -> None:
        pass

    def parse_file(
        self,
        file_path: Union[str, Path],
        display_path: Optional[str] = None,
    ) -> FileParseResult:
        """Parse a single .rpy or .rpym file from disk."""
        disp = display_path or str(file_path).replace("\\", "/")
        source = SourceLoader.load(file_path, display_path=disp)
        return self.parse_source(source)

    def parse_source(self, source: SourceFile) -> FileParseResult:
        """Parse a loaded SourceFile into symbols and errors."""
        result = FileParseResult(file_path=source.file_path)

        if source.encoding_warning:
            result.errors.append(
                ParseError(
                    file_path=source.file_path,
                    line=1,
                    message=source.encoding_warning,
                    severity=Severity.WARNING,
                )
            )

        logical_lines = list(ScriptLexer.tokenize(source.file_path, source.lines))
        self._parse_lines(logical_lines, result)
        return result

    def _parse_lines(
        self,
        lines: list[LogicalLine],
        result: FileParseResult,
    ) -> None:
        """Iterate through logical lines extracting Ren'Py symbols and tracking state."""
        current_global_label: Optional[str] = None
        active_screen_indent: Optional[int] = None
        active_screen_index: int = -1

        menu_stack: list[dict[str, Any]] = []

        pending_dead_stmt: Optional[str] = None
        pending_dead_indent: int = 0
        pending_dead_line: int = 0

        # Tracking state for multi-line Python blocks
        active_python_block: Optional[PythonBlock] = None
        active_python_lines: list[LogicalLine] = []
        python_block_indent: int = 0
        last_python_line_num: int = 0

        pending_action_lines: list[LogicalLine] = []
        pending_action_balance: int = 0
        pending_action_prop: Optional[str] = None

        skip_until_idx: int = -1

        def _record_action(act: ExtractedAction, loc: Location) -> None:
            if act.category == "jump":
                result.jumps.append(
                    JumpReference(
                        target=act.target,
                        location=loc,
                        is_expression=act.is_expression,
                        kind=act.kind,
                        scope_label=current_global_label,
                    )
                )
            elif act.category == "call":
                result.calls.append(
                    CallReference(
                        target=act.target,
                        location=loc,
                        is_expression=act.is_expression,
                        kind=act.kind,
                        is_screen=False,
                        scope_label=current_global_label,
                    )
                )
            elif act.category == "screen":
                result.calls.append(
                    CallReference(
                        target=act.target,
                        location=loc,
                        is_expression=act.is_expression,
                        kind=act.kind,
                        is_screen=True,
                        screen_action=act.screen_action,
                        scope_label=current_global_label,
                    )
                )

        def _finalize_python_block_actions(
            py_block: PythonBlock, py_lines: list[LogicalLine]
        ) -> None:
            if not py_lines:
                return
            block_code = textwrap.dedent("\n".join(pl.raw_text for pl in py_lines))
            actions, err = extract_actions_from_ast(block_code, mode="exec")
            if err:
                result.errors.append(
                    ParseError(
                        file_path=py_block.location.file_path,
                        line=py_block.location.line_number,
                        column=py_block.location.column_number,
                        message=f"Python syntax error in block: {err}",
                        severity=Severity.WARNING,
                        source_snippet=py_block.location.source_snippet,
                    )
                )
            else:
                for act in actions:
                    src_l = py_lines[min(act.line_offset, len(py_lines) - 1)]
                    loc = Location(
                        file_path=src_l.file_path,
                        line_number=src_l.line_number,
                        column_number=src_l.column + act.column_offset,
                        source_snippet=src_l.raw_text.strip(),
                    )
                    _record_action(act, loc)

        for line_idx, line in enumerate(lines):
            try:
                if line_idx < skip_until_idx:
                    continue

                code = line.stripped_code
                if code and ('"' in code or "'" in code):
                    for m1, m2 in RE_QUOTED_STRING.findall(code):
                        s = m1 or m2
                        if s:
                            result.string_literals.append(s)

                # 1. Check if we are inside a Python block
                if active_python_block is not None:
                    if (
                        line.is_empty
                        or line.indent > python_block_indent
                        or line.is_multiline_string_continuation
                    ):
                        if not line.is_empty:
                            last_python_line_num = line.line_number
                            active_python_lines.append(line)
                            if "register_channel" in line.stripped_code:
                                m_reg = RE_REGISTER_CHANNEL.search(line.stripped_code)
                                if m_reg:
                                    result.registered_channels.append(m_reg.group(1))
                            if "custom_text_tags" in line.stripped_code:
                                for m_ct in RE_CUSTOM_TEXT_TAG.finditer(line.stripped_code):
                                    result.custom_text_tags.append(m_ct.group(1))
                                for m_sc in RE_SELF_CLOSING_TEXT_TAG.finditer(line.stripped_code):
                                    result.custom_self_closing_text_tags.append(m_sc.group(1))
                        continue
                    else:
                        # Indentation returned to outer scope; finalize Python block
                        completed_block = PythonBlock(
                            block_type=active_python_block.block_type,
                            location=active_python_block.location,
                            end_line=last_python_line_num,
                        )
                        result.python_blocks.append(completed_block)
                        _finalize_python_block_actions(active_python_block, active_python_lines)
                        active_python_block = None
                        active_python_lines = []

                # Check if indentation returned to outer scope; finalize screen block
                if (
                    active_screen_indent is not None
                    and not line.is_empty
                    and not line.is_multiline_string_continuation
                ):
                    if line.indent <= active_screen_indent:
                        active_screen_indent = None
                        active_screen_index = -1
                    else:
                        m_var = RE_VARIANT_STMT.match(line.stripped_code)
                        if m_var and 0 <= active_screen_index < len(result.screens):
                            sc = result.screens[active_screen_index]
                            result.screens[active_screen_index] = replace(
                                sc, variant=m_var.group(1).strip()
                            )

                # Check if indentation returned to outer scope; finalize menu blocks
                if (
                    menu_stack
                    and not line.is_empty
                    and not line.is_multiline_string_continuation
                    and line.stripped_code
                ):
                    while menu_stack and line.indent <= menu_stack[-1]["indent"]:
                        popped = menu_stack.pop()
                        result.menus.append(
                            MenuBlock(
                                location=popped["location"],
                                item_count=popped["item_count"],
                                scope_label=popped["scope_label"],
                            )
                        )
                    if menu_stack:
                        top = menu_stack[-1]
                        if line.indent > top["indent"] and RE_MENU_ITEM.match(line.stripped_code):
                            if top["items_indent"] is None:
                                top["items_indent"] = line.indent
                            if line.indent == top["items_indent"]:
                                top["item_count"] += 1

                # 2. Skip empty lines or multiline string continuations
                if line.is_empty or line.is_multiline_string_continuation:
                    continue

                code = line.stripped_code

                # Check unreachable dead code immediately following jump or return
                if pending_dead_stmt is not None:
                    if line.indent >= pending_dead_indent:
                        if not code.startswith((
                            "label ", "menu", "init ", "screen ", "define ", "default ",
                            "transform "
                        )):
                            result.unreachables.append(
                                UnreachableStatement(
                                    statement=code,
                                    location=Location(
                                        file_path=line.file_path,
                                        line_number=line.line_number,
                                        column_number=line.column,
                                        source_snippet=line.raw_text.strip(),
                                    ),
                                    preceding_statement=pending_dead_stmt,
                                    preceding_line=pending_dead_line,
                                )
                            )
                    pending_dead_stmt = None

                # Extract dialogue lines / text tags (ignore declarations/screens/tl)
                is_non_dialogue = (
                    code.startswith((
                        "define ", "default ", "image ", "transform ", "style ", "$",
                        "init ", "init:", "layeredimage ", "camera ", "old ", "new "
                    ))
                    or active_screen_indent is not None
                    or "what_prefix" in code
                    or "who_prefix" in code
                )
                can_extract_diag = (
                    active_python_block is None
                    and not is_non_dialogue
                    and "{" in code
                    and "}" in code
                )
                if can_extract_diag:
                    for m1, m2 in RE_QUOTED_STRING.findall(code):
                        text = m1 or m2
                        if "{" in text and "}" in text:
                            clean_t = text.replace("{{", "").replace("}}", "")
                            if "{" in clean_t and "}" in clean_t:
                                result.dialogues.append(
                                DialogueLine(
                                    text=text,
                                    location=Location(
                                        file_path=line.file_path,
                                        line_number=line.line_number,
                                        column_number=line.column,
                                        source_snippet=line.raw_text.strip(),
                                    ),
                                )
                            )

                # Track menu blocks
                is_menu_stmt = code == "menu:" or code.startswith(("menu ", "menu:"))
                if is_menu_stmt and active_screen_indent is None:
                    while menu_stack and line.indent <= menu_stack[-1]["indent"]:
                        popped = menu_stack.pop()
                        result.menus.append(
                            MenuBlock(
                                location=popped["location"],
                                item_count=popped["item_count"],
                                scope_label=popped["scope_label"],
                            )
                        )
                    menu_stack.append(
                        {
                            "location": Location(
                                file_path=line.file_path,
                                line_number=line.line_number,
                                column_number=line.column,
                                source_snippet=line.raw_text.strip(),
                            ),
                            "indent": line.indent,
                            "items_indent": None,
                            "item_count": 0,
                            "scope_label": current_global_label,
                        }
                    )

                # Screen Language handling: actions, multi-line action lists, and inline Python
                if active_screen_indent is not None and line.indent > active_screen_indent:
                    # 1. Multi-line action expression continuation
                    if pending_action_lines:
                        pending_action_lines.append(line)
                        pending_action_balance += calculate_delimiter_balance(line.stripped_code)
                        if pending_action_balance <= 0:
                            raw_first = pending_action_lines[0].raw_text
                            prop_len = len(pending_action_prop) if pending_action_prop else 0
                            p_idx = (
                                raw_first.find(pending_action_prop)
                                if pending_action_prop
                                else -1
                            )
                            first_clean = (
                                raw_first[p_idx + prop_len :]
                                if p_idx != -1
                                else raw_first
                            )
                            cleaned_lines = [first_clean] + [
                                al.raw_text for al in pending_action_lines[1:]
                            ]
                            full_expr = textwrap.dedent("\n".join(cleaned_lines))
                            actions, _ = extract_actions_from_ast(full_expr, mode="eval")
                            if not actions:
                                actions, _ = extract_actions_from_ast(full_expr, mode="exec")
                            for act in actions:
                                max_idx = len(pending_action_lines) - 1
                                src_l = pending_action_lines[min(act.line_offset, max_idx)]
                                loc = Location(
                                    file_path=src_l.file_path,
                                    line_number=src_l.line_number,
                                    column_number=src_l.column + act.column_offset,
                                    source_snippet=src_l.raw_text.strip(),
                                )
                                _record_action(act, loc)
                            pending_action_lines = []
                            pending_action_balance = 0
                            pending_action_prop = None
                        continue

                    # 2. Single-line Python statement inside screen
                    if code.startswith("$"):
                        py_stmt = code[1:].strip()
                        actions, err = extract_actions_from_ast(py_stmt, mode="exec")
                        if err:
                            result.errors.append(
                                ParseError(
                                    file_path=line.file_path,
                                    line=line.line_number,
                                    column=line.column,
                                    message=f"Python syntax error in screen '$' statement: {err}",
                                    severity=Severity.WARNING,
                                    source_snippet=line.raw_text.strip(),
                                )
                            )
                        else:
                            loc = Location(
                                file_path=line.file_path,
                                line_number=line.line_number,
                                column_number=line.column,
                                source_snippet=line.raw_text.strip(),
                            )
                            for act in actions:
                                _record_action(act, loc)
                        continue

                    # 3. Action properties on screen widgets/buttons
                    for prop in ACTION_PROPERTY_PREFIXES:
                        if prop in code:
                            prop_idx = code.find(prop) + len(prop)
                            expr_part = code[prop_idx:].strip()
                            bal = calculate_delimiter_balance(expr_part)
                            if bal > 0:
                                pending_action_lines = [line]
                                pending_action_balance = bal
                                pending_action_prop = prop
                                break
                            else:
                                actions, _ = extract_actions_from_ast(expr_part, mode="eval")
                                if not actions:
                                    actions, _ = extract_actions_from_ast(expr_part, mode="exec")
                                loc = Location(
                                    file_path=line.file_path,
                                    line_number=line.line_number,
                                    column_number=line.column,
                                    source_snippet=line.raw_text.strip(),
                                )
                                for act in actions:
                                    _record_action(act, loc)

                    # Continue past screen lines so they are not parsed as script labels/dialogue
                    continue

                # Single-line Python outside screens
                if code.startswith("$"):
                    if "register_channel" in code:
                        m_reg = RE_REGISTER_CHANNEL.search(code)
                        if m_reg:
                            result.registered_channels.append(m_reg.group(1))
                    if "custom_text_tags" in code:
                        for m_ct in RE_CUSTOM_TEXT_TAG.finditer(code):
                            result.custom_text_tags.append(m_ct.group(1))
                        for m_sc in RE_SELF_CLOSING_TEXT_TAG.finditer(code):
                            result.custom_self_closing_text_tags.append(m_sc.group(1))

                    py_stmt = code[1:].strip()
                    actions, err = extract_actions_from_ast(py_stmt, mode="exec")
                    if err:
                        result.errors.append(
                            ParseError(
                                file_path=line.file_path,
                                line=line.line_number,
                                column=line.column,
                                message=f"Python syntax error in '$' statement: {err}",
                                severity=Severity.WARNING,
                                source_snippet=line.raw_text.strip(),
                            )
                        )
                    else:
                        loc = Location(
                            file_path=line.file_path,
                            line_number=line.line_number,
                            column_number=line.column,
                            source_snippet=line.raw_text.strip(),
                        )
                        for act in actions:
                            _record_action(act, loc)
                    continue

                # Action assignments in define / default statements
                if code.startswith(("define ", "default ")) and "=" in code:
                    rhs = code.split("=", 1)[1].strip()
                    if any(k in rhs for k in ("Jump", "Call", "Show", "Start", "renpy.")):
                        actions, _ = extract_actions_from_ast(rhs, mode="eval")
                        if not actions:
                            actions, _ = extract_actions_from_ast(rhs, mode="exec")
                        loc = Location(
                            file_path=line.file_path,
                            line_number=line.line_number,
                            column_number=line.column,
                            source_snippet=line.raw_text.strip(),
                        )
                        for act in actions:
                            _record_action(act, loc)

                # Fast keyword check: skip regex matching on dialogue / non-statements
                if not code.startswith((
                    "label", "screen", "jump", "call", "image", "play", "queue",
                    "define", "default", "translate", "scene", "show", "hide",
                    "init", "python", "$", "menu", "voice", "layeredimage", "return"
                )) and "register_channel" not in code and "custom_text_tags" not in code:
                    continue

                if "register_channel" in code:
                    m_reg = RE_REGISTER_CHANNEL.search(code)
                    if m_reg:
                        result.registered_channels.append(m_reg.group(1))

                if "custom_text_tags" in code:
                    for m_ct in RE_CUSTOM_TEXT_TAG.finditer(code):
                        result.custom_text_tags.append(m_ct.group(1))
                    for m_sc in RE_SELF_CLOSING_TEXT_TAG.finditer(code):
                        result.custom_self_closing_text_tags.append(m_sc.group(1))

                # Init offset statement: e.g. "init offset = -2"
                if code.startswith("init offset"):
                    m_off = RE_INIT_OFFSET.match(code)
                    if m_off:
                        offset_val = int(m_off.group(1))
                        result.init_statements.append(
                            InitStatement(
                                priority=offset_val,
                                statement_type="init offset",
                                location=Location(
                                    file_path=line.file_path,
                                    line_number=line.line_number,
                                    column_number=line.column,
                                    source_snippet=line.raw_text.strip(),
                                ),
                            )
                        )
                        continue

                # Init blocks: "init ...:" or "init python ...:"
                if code.startswith("init") and code.endswith(":"):
                    m_init = RE_INIT_STMT.match(code)
                    if m_init:
                        priority_str = m_init.group(1)
                        if priority_str is not None:
                            p_val = int(priority_str)
                            stmt_type = "init python" if "python" in code else "init"
                            result.init_statements.append(
                                InitStatement(
                                    priority=p_val,
                                    statement_type=stmt_type,
                                    location=Location(
                                        file_path=line.file_path,
                                        line_number=line.line_number,
                                        column_number=line.column,
                                        source_snippet=line.raw_text.strip(),
                                    ),
                                )
                            )

                # 3. Detect Python block start
                if code.startswith(("python", "init")) and RE_PYTHON_BLOCK.match(code):
                    block_type = code.rstrip(":").strip()
                    active_python_block = PythonBlock(
                        block_type=block_type,
                        location=Location(
                            file_path=line.file_path,
                            line_number=line.line_number,
                            column_number=line.column,
                            source_snippet=line.raw_text.strip(),
                        ),
                        end_line=line.line_number,
                    )
                    python_block_indent = line.indent
                    last_python_line_num = line.line_number
                    continue

                # 4. Labels & Named Menus (ignore UI label inside screens)
                is_label_or_menu = code.startswith("label ") or code.startswith("menu ")
                if is_label_or_menu and active_screen_indent is None:
                    is_menu_def = code.startswith("menu ")
                    m_label = (
                        RE_LABEL.match(code)
                        if not is_menu_def
                        else RE_MENU.match(code)
                    )
                    if not m_label and not code.endswith(":") and "(" in code:
                        # Multiline signature
                        parts = [code]
                        for k in range(line_idx + 1, len(lines)):
                            next_l = lines[k]
                            if not next_l.is_empty:
                                parts.append(next_l.stripped_code)
                                if next_l.stripped_code.endswith(":"):
                                    skip_until_idx = k + 1
                                    break
                        accumulated = " ".join(parts)
                        m_label = (
                            RE_LABEL.match(accumulated)
                            if not is_menu_def
                            else RE_MENU.match(accumulated)
                        )

                    if m_label:
                        label_name = m_label.group(1)
                        if label_name == "_":
                            continue

                        params = m_label.group(2)
                        is_local = label_name.startswith(".")

                        parent_lbl = current_global_label if is_local else None
                        if not is_local:
                            current_global_label = label_name

                        result.labels.append(
                            LabelSymbol(
                                name=label_name,
                                location=Location(
                                    file_path=line.file_path,
                                    line_number=line.line_number,
                                    column_number=line.column,
                                    source_snippet=line.raw_text.strip(),
                                ),
                                is_local=is_local,
                                parent_label=parent_lbl,
                                params=params.strip() if params else None,
                                is_menu=is_menu_def,
                            )
                        )
                        continue

                # 4b. Screens
                if code.startswith("screen "):
                    m_screen = RE_SCREEN.match(code)
                    var_header = None
                    if not m_screen and not code.endswith(":") and "(" in code:
                        # Multiline screen parameter signature
                        parts = [code]
                        for k in range(line_idx + 1, len(lines)):
                            next_l = lines[k]
                            if not next_l.is_empty:
                                parts.append(next_l.stripped_code)
                                if next_l.stripped_code.endswith(":"):
                                    skip_until_idx = k + 1
                                    break
                        accumulated = " ".join(parts)
                        m_screen = RE_SCREEN.match(accumulated)
                        if m_screen:
                            m_vh = RE_VARIANT_HEADER.search(accumulated)
                            if m_vh:
                                var_header = m_vh.group(1).strip()

                    if m_screen:
                        screen_name = m_screen.group(1).strip()
                        params = m_screen.group(2)
                        active_screen_indent = line.indent
                        if var_header is None:
                            m_vh = RE_VARIANT_HEADER.search(code)
                            if m_vh:
                                var_header = m_vh.group(1).strip()
                        result.screens.append(
                            ScreenDefinition(
                                name=screen_name,
                                location=Location(
                                    file_path=line.file_path,
                                    line_number=line.line_number,
                                    column_number=line.column,
                                    source_snippet=line.raw_text.strip(),
                                ),
                                params=params.strip() if params else None,
                                variant=var_header,
                            )
                        )
                        active_screen_index = len(result.screens) - 1
                        continue

                # 5. Jumps
                if code.startswith("jump "):
                    m_jump = RE_JUMP.match(code)
                    if m_jump:
                        raw_target = m_jump.group(1).strip()
                        if raw_target.startswith("expression "):
                            expr_val = raw_target[len("expression ") :].strip()
                            result.jumps.append(
                                JumpReference(
                                    target=expr_val,
                                    location=Location(
                                        file_path=line.file_path,
                                        line_number=line.line_number,
                                        column_number=line.column,
                                        source_snippet=line.raw_text.strip(),
                                    ),
                                    is_expression=True,
                                    kind=ReferenceKind.DYNAMIC,
                                    scope_label=current_global_label,
                                )
                            )
                        else:
                            result.jumps.append(
                                JumpReference(
                                    target=raw_target,
                                    location=Location(
                                        file_path=line.file_path,
                                        line_number=line.line_number,
                                        column_number=line.column,
                                        source_snippet=line.raw_text.strip(),
                                    ),
                                    is_expression=False,
                                    kind=ReferenceKind.STATIC,
                                    scope_label=current_global_label,
                                )
                            )
                            can_track_dead = (
                                active_python_block is None
                                and active_screen_indent is None
                                and not code.endswith(":")
                            )
                            if can_track_dead:
                                pending_dead_stmt = code
                                pending_dead_indent = line.indent
                                pending_dead_line = line.line_number
                        continue

                # 6. Calls
                if code.startswith("call "):
                    m_call = RE_CALL.match(code)
                    if m_call:
                        raw_call = m_call.group(1).strip()
                        if raw_call.startswith("screen "):
                            # Screen call: e.g. "call screen preferences with dissolve"
                            screen_target = raw_call[len("screen ") :].strip()
                            for clause in (" with ", " nopredict", " pass", " as ", "("):
                                if clause in screen_target:
                                    screen_target = screen_target.split(clause)[0].strip()
                            result.calls.append(
                                CallReference(
                                    target=screen_target,
                                    location=Location(
                                        file_path=line.file_path,
                                        line_number=line.line_number,
                                        column_number=line.column,
                                        source_snippet=line.raw_text.strip(),
                                    ),
                                    is_expression=False,
                                    kind=ReferenceKind.STATIC,
                                    is_screen=True,
                                    screen_action="call",
                                    scope_label=current_global_label,
                                )
                            )
                        elif raw_call.startswith("expression "):
                            expr_val = raw_call[len("expression ") :].strip()
                            result.calls.append(
                                CallReference(
                                    target=expr_val,
                                    location=Location(
                                        file_path=line.file_path,
                                        line_number=line.line_number,
                                        column_number=line.column,
                                        source_snippet=line.raw_text.strip(),
                                    ),
                                    is_expression=True,
                                    kind=ReferenceKind.DYNAMIC,
                                    is_screen=False,
                                    scope_label=current_global_label,
                                )
                            )
                        else:
                            # Static label call: "call my_label(arg)" or "call my_label from _label"
                            target_clean = raw_call.split("(")[0].split(" from ")[0].strip()
                            result.calls.append(
                                CallReference(
                                    target=target_clean,
                                    location=Location(
                                        file_path=line.file_path,
                                        line_number=line.line_number,
                                        column_number=line.column,
                                        source_snippet=line.raw_text.strip(),
                                    ),
                                    is_expression=False,
                                    kind=ReferenceKind.STATIC,
                                    is_screen=False,
                                    scope_label=current_global_label,
                                )
                            )
                        continue

                # 7. Images
                m_img_eq = RE_IMAGE_EQUAL.match(code)
                if m_img_eq:
                    img_name = m_img_eq.group(1).strip()
                    raw_val = m_img_eq.group(2).strip()
                    unquoted = unquote_string(raw_val)
                    is_dyn = unquoted is None or ("[" in unquoted and "]" in unquoted)
                    result.images.append(
                        ImageDefinition(
                            name=img_name,
                            location=Location(
                                file_path=line.file_path,
                                line_number=line.line_number,
                                column_number=line.column,
                                source_snippet=line.raw_text.strip(),
                            ),
                            asset_reference=unquoted,
                            is_dynamic=is_dyn,
                        )
                    )
                    continue

                m_img_atl = RE_IMAGE_ATL.match(code)
                if m_img_atl:
                    img_name = m_img_atl.group(1).strip()
                    result.images.append(
                        ImageDefinition(
                            name=img_name,
                            location=Location(
                                file_path=line.file_path,
                                line_number=line.line_number,
                                column_number=line.column,
                                source_snippet=line.raw_text.strip(),
                            ),
                            asset_reference=None,
                            is_dynamic=True,
                        )
                    )
                    continue

                if code.startswith("layeredimage "):
                    m_lay = RE_LAYEREDIMAGE.match(code)
                    if m_lay:
                        img_name = m_lay.group(1).strip()
                        result.images.append(
                            ImageDefinition(
                                name=img_name,
                                location=Location(
                                    file_path=line.file_path,
                                    line_number=line.line_number,
                                    column_number=line.column,
                                    source_snippet=line.raw_text.strip(),
                                ),
                                asset_reference=None,
                                is_dynamic=False,
                            )
                        )
                        continue

                # 8. Audio (play / queue / voice)
                m_audio_list = RE_AUDIO_LIST.match(code)
                if m_audio_list:
                    action = m_audio_list.group(1)
                    channel = m_audio_list.group(2)
                    list_body = m_audio_list.group(3)
                    quoted_items = RE_QUOTED_ITEM.findall(list_body)
                    if quoted_items:
                        for raw_path in quoted_items:
                            clauses, clean_audio, is_q = parse_audio_target(raw_path)
                            result.audios.append(
                                AudioReference(
                                    channel=channel,
                                    target=clean_audio,
                                    action=action,
                                    location=Location(
                                        file_path=line.file_path,
                                        line_number=line.line_number,
                                        column_number=line.column,
                                        source_snippet=line.raw_text.strip(),
                                    ),
                                    kind=ReferenceKind.STATIC,
                                    is_quoted=True,
                                    clauses=clauses,
                                    clean_target=clean_audio,
                                )
                            )
                    else:
                        for raw_item in list_body.split(","):
                            dyn_target = raw_item.strip()
                            if dyn_target:
                                clauses, clean_dyn, is_q = parse_audio_target(dyn_target)
                                result.audios.append(
                                    AudioReference(
                                        channel=channel,
                                        target=dyn_target,
                                        action=action,
                                        location=Location(
                                            file_path=line.file_path,
                                            line_number=line.line_number,
                                            column_number=line.column,
                                            source_snippet=line.raw_text.strip(),
                                        ),
                                        kind=ReferenceKind.DYNAMIC,
                                        is_quoted=False,
                                        clauses=clauses,
                                        clean_target=clean_dyn,
                                    )
                                )
                    continue

                m_audio_q = RE_AUDIO_QUOTED.match(code)
                if m_audio_q:
                    action = m_audio_q.group(1)
                    channel = m_audio_q.group(2)
                    raw_path = m_audio_q.group(3)
                    clauses, clean_audio, _ = parse_audio_target(raw_path)
                    result.audios.append(
                        AudioReference(
                            channel=channel,
                            target=clean_audio,
                            action=action,
                            location=Location(
                                file_path=line.file_path,
                                line_number=line.line_number,
                                column_number=line.column,
                                source_snippet=line.raw_text.strip(),
                            ),
                            kind=ReferenceKind.STATIC,
                            is_quoted=True,
                            clauses=clauses,
                            clean_target=clean_audio,
                        )
                    )
                    continue

                m_audio_dyn = RE_AUDIO_DYNAMIC.match(code)
                if m_audio_dyn:
                    action = m_audio_dyn.group(1)
                    channel = m_audio_dyn.group(2)
                    dyn_target = m_audio_dyn.group(3)
                    clauses, clean_dyn, _ = parse_audio_target(dyn_target)
                    result.audios.append(
                        AudioReference(
                            channel=channel,
                            target=dyn_target,
                            action=action,
                            location=Location(
                                file_path=line.file_path,
                                line_number=line.line_number,
                                column_number=line.column,
                                source_snippet=line.raw_text.strip(),
                            ),
                            kind=ReferenceKind.DYNAMIC,
                            is_quoted=False,
                            clauses=clauses,
                            clean_target=clean_dyn,
                        )
                    )
                    continue

                m_voice_q = RE_VOICE_QUOTED.match(code)
                if m_voice_q:
                    raw_path = m_voice_q.group(1)
                    clauses, clean_voice, _ = parse_audio_target(raw_path)
                    result.audios.append(
                        AudioReference(
                            channel="voice",
                            target=clean_voice,
                            action="voice",
                            location=Location(
                                file_path=line.file_path,
                                line_number=line.line_number,
                                column_number=line.column,
                                source_snippet=line.raw_text.strip(),
                            ),
                            kind=ReferenceKind.STATIC,
                            is_quoted=True,
                            clauses=clauses,
                            clean_target=clean_voice,
                        )
                    )
                    continue

                m_voice_dyn = RE_VOICE_DYNAMIC.match(code)
                if m_voice_dyn:
                    dyn_target = m_voice_dyn.group(1)
                    clauses, clean_voice, _ = parse_audio_target(dyn_target)
                    result.audios.append(
                        AudioReference(
                            channel="voice",
                            target=dyn_target,
                            action="voice",
                            location=Location(
                                file_path=line.file_path,
                                line_number=line.line_number,
                                column_number=line.column,
                                source_snippet=line.raw_text.strip(),
                            ),
                            kind=ReferenceKind.DYNAMIC,
                            is_quoted=False,
                            clauses=clauses,
                            clean_target=clean_voice,
                        )
                    )
                    continue

                # 9. Define / Default
                m_def = RE_DEFINE_DEFAULT.match(code)
                if m_def:
                    kind = m_def.group(1)
                    priority_str = m_def.group(2)
                    var_name = m_def.group(3)
                    raw_val = m_def.group(4).strip()
                    priority = int(priority_str.strip()) if priority_str else None

                    result.variables.append(
                        VariableDeclaration(
                            name=var_name,
                            kind=kind,
                            location=Location(
                                file_path=line.file_path,
                                line_number=line.line_number,
                                column_number=line.column,
                                source_snippet=line.raw_text.strip(),
                            ),
                            raw_value=raw_val,
                            priority=priority,
                        )
                    )
                    continue

                # 10. Translate
                m_trans = RE_TRANSLATE.match(code)
                if m_trans:
                    lang = m_trans.group(1)
                    ident = m_trans.group(2).strip()
                    result.translations.append(
                        TranslateBlock(
                            language=lang,
                            identifier=ident,
                            location=Location(
                                file_path=line.file_path,
                                line_number=line.line_number,
                                column_number=line.column,
                                source_snippet=line.raw_text.strip(),
                            ),
                        )
                    )
                    continue

                # 11. Show screen / Hide screen
                if code.startswith(("show screen ", "hide screen ")):
                    m_scr = RE_SHOW_SCREEN.match(code)
                    if m_scr:
                        action_name = m_scr.group(1).lower()
                        screen_name = m_scr.group(2).strip()
                        for clause in (" with ", " nopredict", " pass", " as ", " onlayer ", "("):
                            if clause in screen_name:
                                screen_name = screen_name.split(clause)[0].strip()
                        if screen_name:
                            result.calls.append(
                                CallReference(
                                    target=screen_name,
                                    location=Location(
                                        file_path=line.file_path,
                                        line_number=line.line_number,
                                        column_number=line.column,
                                        source_snippet=line.raw_text.strip(),
                                    ),
                                    is_expression=False,
                                    kind=ReferenceKind.STATIC,
                                    is_screen=True,
                                    screen_action=action_name,
                                    scope_label=current_global_label,
                                )
                            )
                        continue

                # 12. Scene and Show statements
                if code.startswith(("scene ", "show ")):
                    m_scene = RE_SCENE_SHOW.match(code)
                    if m_scene:
                        raw_tag = m_scene.group(2).strip()
                        for clause in (" with ", " at ", " as ", " onlayer ", " behind "):
                            if clause in raw_tag:
                                raw_tag = raw_tag.split(clause)[0].strip()
                        if raw_tag:
                            result.scenes_and_shows.append(raw_tag)
                        continue

                # 13. Return statements
                is_ret = code == "return" or code.startswith("return ")
                if is_ret and active_python_block is None and active_screen_indent is None:
                    if not code.endswith(("(", "[", "{", ",", "\\")):
                        pending_dead_stmt = code
                        pending_dead_indent = line.indent
                        pending_dead_line = line.line_number
                        continue

            except Exception as exc:  # Recover safely from any per-line parsing exception
                result.errors.append(
                    ParseError(
                        file_path=line.file_path,
                        line=line.line_number,
                        column=line.column,
                        message=f"Syntax parsing exception: {exc}",
                        severity=Severity.WARNING,
                        source_snippet=line.raw_text.strip(),
                    )
                )

        # Finalize any pending menu blocks at end of file
        while menu_stack:
            popped = menu_stack.pop()
            result.menus.append(
                MenuBlock(
                    location=popped["location"],
                    item_count=popped["item_count"],
                    scope_label=popped["scope_label"],
                )
            )

        # Finalize any pending Python block at end of file
        if active_python_block is not None:
            completed_block = PythonBlock(
                block_type=active_python_block.block_type,
                location=active_python_block.location,
                end_line=last_python_line_num or active_python_block.location.line_number,
            )
            result.python_blocks.append(completed_block)
            _finalize_python_block_actions(active_python_block, active_python_lines)
            active_python_block = None
            active_python_lines = []

        # Finalize any pending multi-line action at end of file
        if pending_action_lines:
            full_expr = "\n".join(al.raw_text for al in pending_action_lines)
            actions, _ = extract_actions_from_ast(full_expr, mode="eval")
            if not actions:
                actions, _ = extract_actions_from_ast(full_expr, mode="exec")
            for act in actions:
                max_idx = len(pending_action_lines) - 1
                src_l = pending_action_lines[min(act.line_offset, max_idx)]
                loc = Location(
                    file_path=src_l.file_path,
                    line_number=src_l.line_number,
                    column_number=src_l.column + act.column_offset,
                    source_snippet=src_l.raw_text.strip(),
                )
                _record_action(act, loc)
            pending_action_lines = []
