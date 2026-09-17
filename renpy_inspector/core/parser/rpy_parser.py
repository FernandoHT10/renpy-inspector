"""Deterministic static parser for Ren'Py scripts (.rpy and .rpym)."""

import re
from pathlib import Path
from typing import Optional, Union

from renpy_inspector.core.models.enums import Severity
from renpy_inspector.core.models.location import Location
from renpy_inspector.core.models.symbols import (
    AudioReference,
    CallReference,
    ImageDefinition,
    JumpReference,
    LabelSymbol,
    PythonBlock,
    ReferenceKind,
    ScreenDefinition,
    TranslateBlock,
    VariableDeclaration,
)
from renpy_inspector.core.parser.errors import ParseError
from renpy_inspector.core.parser.lexer import LogicalLine, ScriptLexer
from renpy_inspector.core.parser.result import FileParseResult
from renpy_inspector.core.parser.source import SourceFile, SourceLoader

# Regex patterns for Ren'Py statements (using Unicode-aware word matching)
RE_LABEL = re.compile(r"^label\s+([\w\.]+)(?:\s*\((.*)\))?\s*:$", re.UNICODE)
RE_MENU = re.compile(r"^menu\s+([\w\.]+)(?:\s*\((.*)\))?\s*:$", re.UNICODE)
RE_SCREEN = re.compile(r"^screen\s+([\w\.]+)(?:\s*\((.*)\))?.*:$", re.UNICODE)
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
RE_PYTHON_BLOCK = re.compile(r"^(init\s+(-?\d+\s+)?)*python(\s+(early|hide))?\s*:$", re.UNICODE)
RE_SCENE_SHOW = re.compile(r"^(scene|show)\s+([^:\n\r]+)", re.UNICODE)
RE_SHOW_SCREEN = re.compile(r"^(show|hide)\s+screen\s+([\w\.]+)(.*)$", re.UNICODE)
RE_REGISTER_CHANNEL = re.compile(r"register_channel\s*\(\s*[\"']([\w]+)[\"']", re.UNICODE)


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

        # Tracking state for multi-line Python blocks
        active_python_block: Optional[PythonBlock] = None
        python_block_indent: int = 0
        last_python_line_num: int = 0

        for line in lines:
            try:
                # 1. Check if we are inside a Python block
                if active_python_block is not None:
                    if line.is_empty or line.indent > python_block_indent:
                        if not line.is_empty:
                            last_python_line_num = line.line_number
                            if "register_channel" in line.stripped_code:
                                m_reg = RE_REGISTER_CHANNEL.search(line.stripped_code)
                                if m_reg:
                                    result.registered_channels.append(m_reg.group(1))
                        continue
                    else:
                        # Indentation returned to outer scope; finalize Python block
                        completed_block = PythonBlock(
                            block_type=active_python_block.block_type,
                            location=active_python_block.location,
                            end_line=last_python_line_num,
                        )
                        result.python_blocks.append(completed_block)
                        active_python_block = None

                # Check if indentation returned to outer scope; finalize screen block
                if active_screen_indent is not None and not line.is_empty:
                    if line.indent <= active_screen_indent:
                        active_screen_indent = None

                # 2. Skip empty lines or multiline string continuations
                if line.is_empty or line.is_multiline_string_continuation:
                    continue

                code = line.stripped_code

                # Fast keyword check: skip regex matching on dialogue / non-statements
                if not code.startswith((
                    "label", "screen", "jump", "call", "image", "play", "queue",
                    "define", "default", "translate", "scene", "show", "hide",
                    "init", "python", "$", "menu", "voice", "layeredimage"
                )) and "register_channel" not in code:
                    continue

                if "register_channel" in code:
                    m_reg = RE_REGISTER_CHANNEL.search(code)
                    if m_reg:
                        result.registered_channels.append(m_reg.group(1))

                # 3. Detect Python block start
                if code.startswith(("python", "init ")) and RE_PYTHON_BLOCK.match(code):
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
                    m_label = (
                        RE_LABEL.match(code)
                        if code.startswith("label ")
                        else RE_MENU.match(code)
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
                            )
                        )
                        continue

                # 4b. Screens
                if code.startswith("screen "):
                    m_screen = RE_SCREEN.match(code)
                    if m_screen:
                        screen_name = m_screen.group(1).strip()
                        params = m_screen.group(2)
                        active_screen_indent = line.indent
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
                            )
                        )
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
                            unquoted_audio = unquote_string(raw_path) or raw_path
                            clean_audio = RE_AUDIO_CLAUSE.sub("", unquoted_audio)
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
                                )
                            )
                    else:
                        for raw_item in list_body.split(","):
                            dyn_target = raw_item.strip()
                            if dyn_target:
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
                                    )
                                )
                    continue

                m_audio_q = RE_AUDIO_QUOTED.match(code)
                if m_audio_q:
                    action = m_audio_q.group(1)
                    channel = m_audio_q.group(2)
                    raw_path = m_audio_q.group(3)
                    unquoted_audio = unquote_string(raw_path) or raw_path
                    clean_audio = RE_AUDIO_CLAUSE.sub("", unquoted_audio)
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
                        )
                    )
                    continue

                m_audio_dyn = RE_AUDIO_DYNAMIC.match(code)
                if m_audio_dyn:
                    action = m_audio_dyn.group(1)
                    channel = m_audio_dyn.group(2)
                    dyn_target = m_audio_dyn.group(3)
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
                        )
                    )
                    continue

                m_voice_q = RE_VOICE_QUOTED.match(code)
                if m_voice_q:
                    raw_path = m_voice_q.group(1)
                    unquoted_voice = unquote_string(raw_path) or raw_path
                    clean_voice = RE_AUDIO_CLAUSE.sub("", unquoted_voice)
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
                        )
                    )
                    continue

                m_voice_dyn = RE_VOICE_DYNAMIC.match(code)
                if m_voice_dyn:
                    dyn_target = m_voice_dyn.group(1)
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

        # Finalize any pending Python block at end of file
        if active_python_block is not None:
            completed_block = PythonBlock(
                block_type=active_python_block.block_type,
                location=active_python_block.location,
                end_line=last_python_line_num or active_python_block.location.line_number,
            )
            result.python_blocks.append(completed_block)
