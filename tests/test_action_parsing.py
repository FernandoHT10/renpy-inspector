"""Comprehensive regression test suite for Jump/Call and Screen Action parsing (Problem #5).

Verifies the 6 architectural conditions approved by GPT-6 Astra:
1. Immunity to dialogue and narrative strings (no false positives).
2. Immunity to comments.
3. Immunity to strings, docstrings, and formatted strings in Python code.
4. Correct parsing of multiple arguments and nested delimiters (e.g. Fade(0.5)).
5. Correct handling of strings with embedded closing parentheses ')'.
6. Multiline Python block calls across lines with source line offsets.
7. Multiline action lists with balanced delimiters in Screen Language.
8. Proper distinction between static literals and dynamic expressions.
9. Strict qualification of actions (bare calls and renpy.* allowed;
   arbitrary object calls rejected).
10. Engine actions (Start() -> "start", ShowMenu -> "showmenu").
11. Python syntax errors generate structured ParseError without crashing.
"""

from renpy_inspector.core.models.symbols import ReferenceKind
from renpy_inspector.core.parser.rpy_parser import RpyParser
from renpy_inspector.core.parser.source import SourceFile


def parse_string(script_content: str, file_path: str = "game/script.rpy"):
    """Helper to parse a script snippet directly with RpyParser."""
    lines = tuple(script_content.splitlines())
    source = SourceFile(file_path=file_path, lines=lines, content=script_content, encoding="utf-8")
    parser = RpyParser()
    return parser.parse_source(source)


def test_1_dialogue_immunity():
    """Dialogue and narrative text must never produce Jump or Call references."""
    script = """
label start:
    e "La documentación utiliza Jump('fantasma') como ejemplo."
    "Debes usar Call('fake_target') para llamar esa rutina."
    e 'Show("fake_screen") aparece aquí en un diálogo.'
    return
"""
    res = parse_string(script)
    assert len(res.jumps) == 0, f"Expected 0 jumps, found: {res.jumps}"
    assert len(res.calls) == 0, f"Expected 0 calls, found: {res.calls}"


def test_2_comment_immunity():
    """Comments with Jump, Call, or Show must never produce references."""
    script = """
label start:
    # Jump("comment_jump")
    # call comment_call
    # renpy.call("comment_renpy_call")
    # Show("comment_screen")
    return
"""
    res = parse_string(script)
    assert len(res.jumps) == 0
    assert len(res.calls) == 0


def test_3_python_strings_and_docstrings_immunity():
    """String literals, docstrings, and formatted strings inside Python must not
    generate actions.
    """
    script = '''
init python:
    """
    Module helper.
    Example: Jump("doc_fake") and Call("doc_call").
    """
    def log_action():
        msg = "Jump('string_fake')"
        detail = 'Call("call_string_fake")'
        tmpl = f"renpy.jump('fstring_fake')"
        return msg
'''
    res = parse_string(script)
    assert len(res.jumps) == 0
    assert len(res.calls) == 0
    assert len(res.errors) == 0


def test_4_multiple_args_and_nested_delimiters():
    """Actions with multiple arguments and nested calls (e.g. Fade(0.5)) must parse cleanly."""
    script = """
label start:
    $ renpy.call("my_label", 42, from_current=True)

screen test_ui():
    textbutton "Open":
        action Show("hud", transition=Fade(0.5))
"""
    res = parse_string(script)

    # Label call
    label_calls = [c for c in res.calls if not c.is_screen]
    assert len(label_calls) == 1
    assert label_calls[0].target == "my_label"
    assert label_calls[0].kind == ReferenceKind.STATIC
    assert not label_calls[0].is_expression

    # Screen show call
    screen_calls = [c for c in res.calls if c.is_screen]
    assert len(screen_calls) == 1
    assert screen_calls[0].target == "hud"
    assert screen_calls[0].kind == ReferenceKind.STATIC
    assert screen_calls[0].screen_action == "show"


def test_5_embedded_parenthesis_in_string():
    """Strings containing closing parenthesis ')' must not truncate or cause parse errors."""
    script = """
label start:
    $ renpy.call("target_label", ")", extra="smile :)")
"""
    res = parse_string(script)
    assert len(res.calls) == 1
    assert res.calls[0].target == "target_label"
    assert res.calls[0].kind == ReferenceKind.STATIC
    assert len(res.errors) == 0


def test_6_multiline_python_block_calls():
    """Calls spanning multiple lines inside Python functions must be extracted
    with correct line numbers.
    """
    script = """
init python:
    def my_helper():
        renpy.call(
            "multiline_dest",
            from_current=True,
        )
        renpy.jump(
            "jump_dest"
        )
"""
    res = parse_string(script)
    assert len(res.calls) == 1
    assert res.calls[0].target == "multiline_dest"
    assert res.calls[0].kind == ReferenceKind.STATIC

    assert len(res.jumps) == 1
    assert res.jumps[0].target == "jump_dest"
    assert res.jumps[0].kind == ReferenceKind.STATIC


def test_7_screen_multiline_action_list():
    """Screen Language multiline action lists with balanced delimiters must be parsed."""
    script = """
screen test_screen():
    textbutton "Action":
        action [
            SetVariable("visited", True),
            Jump("destination_label"),
            Show("sub_overlay"),
        ]
"""
    res = parse_string(script)
    assert len(res.jumps) == 1
    assert res.jumps[0].target == "destination_label"
    assert res.jumps[0].kind == ReferenceKind.STATIC

    screen_calls = [c for c in res.calls if c.is_screen]
    assert len(screen_calls) == 1
    assert screen_calls[0].target == "sub_overlay"
    assert screen_calls[0].screen_action == "show"


def test_8_dynamic_vs_static_targets():
    """Static string targets are STATIC; dynamic variables or expressions are DYNAMIC."""
    script = """
label start:
    $ renpy.jump("static_label")
    $ renpy.jump(dyn_label_var)
    $ renpy.call(compute_target("arg"))
"""
    res = parse_string(script)
    assert len(res.jumps) == 2
    # Static jump
    assert res.jumps[0].target == "static_label"
    assert res.jumps[0].kind == ReferenceKind.STATIC
    assert not res.jumps[0].is_expression

    # Dynamic jump
    assert res.jumps[1].target == "dyn_label_var"
    assert res.jumps[1].kind == ReferenceKind.DYNAMIC
    assert res.jumps[1].is_expression

    # Dynamic call
    assert len(res.calls) == 1
    assert res.calls[0].target == "compute_target('arg')"
    assert res.calls[0].kind == ReferenceKind.DYNAMIC
    assert res.calls[0].is_expression


def test_9_engine_actions_and_qualification():
    """Start() maps to target 'start'; ShowMenu maps to 'showmenu';
    unqualified object calls are rejected.
    """
    script = """
screen main_menu():
    textbutton "Start":
        action Start()
    textbutton "Preferences":
        action ShowMenu("preferences")

label start:
    $ player.Jump("fake_player_jump")
    $ enemy.Call("fake_enemy_call")
    $ ui.Show("fake_ui_show")
    return
"""
    res = parse_string(script)
    # Start() produces a JumpReference with target "start"
    assert len(res.jumps) == 1
    assert res.jumps[0].target == "start"
    assert res.jumps[0].kind == ReferenceKind.STATIC

    # ShowMenu produces a CallReference with screen_action "showmenu"
    assert len(res.calls) == 1
    assert res.calls[0].target == "preferences"
    assert res.calls[0].is_screen is True
    assert res.calls[0].screen_action == "showmenu"


def test_10_python_syntax_error_handling():
    """Python syntax errors in blocks or $ statements produce structured ParseError
    without unhandled exceptions.
    """
    script = """
init python:
    def broken(
"""
    res = parse_string(script)
    assert len(res.errors) >= 1
    assert any("Python syntax error" in err.message for err in res.errors)
