"""Comprehensive unit tests for the Ren'Py static parser (Phase 2)."""

from pathlib import Path

from renpy_inspector.core.models.symbols import ReferenceKind
from renpy_inspector.core.parser.lexer import strip_comment_and_track_strings
from renpy_inspector.core.parser.project_parser import ProjectParser
from renpy_inspector.core.parser.rpy_parser import RpyParser
from renpy_inspector.core.parser.source import SourceFile, SourceLoader


def parse_string(script_content: str, file_path: str = "game/script.rpy"):
    """Helper to parse a script snippet directly with RpyParser."""
    lines = tuple(script_content.splitlines())
    source = SourceFile(file_path=file_path, lines=lines, content=script_content, encoding="utf-8")
    parser = RpyParser()
    return parser.parse_source(source)


def test_1_single_label():
    """Test 1: Extract exactly one label."""
    script = "label start:\n    return\n"
    res = parse_string(script)
    assert len(res.labels) == 1
    assert res.labels[0].name == "start"
    assert not res.labels[0].is_local
    assert res.labels[0].parent_label is None
    assert res.labels[0].location.line_number == 1


def test_2_multiple_labels():
    """Test 2: Extract multiple labels."""
    script = """
label start:
    jump chapter

label chapter:
    return
"""
    res = parse_string(script)
    assert len(res.labels) == 2
    assert [lbl.name for lbl in res.labels] == ["start", "chapter"]


def test_3_jump():
    """Test 3: Extract static jump reference."""
    script = """
label start:
    jump chapter_2
"""
    res = parse_string(script)
    assert len(res.jumps) == 1
    jump = res.jumps[0]
    assert jump.target == "chapter_2"
    assert jump.kind == ReferenceKind.STATIC
    assert not jump.is_expression
    assert jump.scope_label == "start"


def test_4_call():
    """Test 4: Extract static call reference and strip arguments."""
    script = """
label start:
    call chapter_2(arg1, arg2)
    call rightaway from _call_rightaway
"""
    res = parse_string(script)
    assert len(res.calls) == 2
    assert res.calls[0].target == "chapter_2"
    assert res.calls[0].kind == ReferenceKind.STATIC
    assert not res.calls[0].is_screen
    assert res.calls[1].target == "rightaway"


def test_4b_call_screen():
    """Test 4b: Call screen should be marked as screen call."""
    script = """
label start:
    call screen preferences()
"""
    res = parse_string(script)
    assert len(res.calls) == 1
    call = res.calls[0]
    assert call.target == "preferences"
    assert call.is_screen


def test_5_dynamic_jump_and_call():
    """Test 5: Jump and call expressions must be flagged as dynamic references."""
    script = """
label start:
    jump expression destination_var
    call expression "chap_" + str(num)
"""
    res = parse_string(script)
    assert len(res.jumps) == 1
    assert res.jumps[0].target == "destination_var"
    assert res.jumps[0].kind == ReferenceKind.DYNAMIC
    assert res.jumps[0].is_expression

    assert len(res.calls) == 1
    assert res.calls[0].target == '"chap_" + str(num)'
    assert res.calls[0].kind == ReferenceKind.DYNAMIC
    assert res.calls[0].is_expression


def test_6_local_label_scope():
    """Test 6: Local labels with leading dot preserve parent scope relationship."""
    script = """
label chapter:
    jump .choice

label .choice:
    return

label chapter2:
    jump .choice
"""
    res = parse_string(script)
    assert len(res.labels) == 3
    lbl_chap = res.labels[0]
    lbl_choice = res.labels[1]
    lbl_chap2 = res.labels[2]

    assert lbl_chap.name == "chapter"
    assert not lbl_chap.is_local

    assert lbl_choice.name == ".choice"
    assert lbl_choice.is_local
    assert lbl_choice.parent_label == "chapter"
    assert lbl_choice.full_name == "chapter.choice"

    assert lbl_chap2.name == "chapter2"
    assert not lbl_chap2.is_local

    assert res.jumps[0].target == ".choice"
    assert res.jumps[0].scope_label == "chapter"
    assert res.jumps[1].scope_label == "chapter2"


def test_7_image_declarations():
    """Test 7: Extract explicit static image references and dynamic ATL blocks."""
    script = """
image bg room = "images/room.png"
image eileen smile = 'images/eileen_smile.webp'
image eileen dynamic = Movie(play="anim.ogv")
image eileen animated:
    "eileen 1"
    pause 1.0
    "eileen 2"
"""
    res = parse_string(script)
    assert len(res.images) == 4

    img1 = res.images[0]
    assert img1.name == "bg room"
    assert img1.tag == "bg"
    assert img1.attributes == ("room",)
    assert img1.asset_reference == "images/room.png"
    assert not img1.is_dynamic

    img2 = res.images[1]
    assert img2.name == "eileen smile"
    assert img2.asset_reference == "images/eileen_smile.webp"
    assert not img2.is_dynamic

    img3 = res.images[2]
    assert img3.name == "eileen dynamic"
    assert img3.asset_reference is None
    assert img3.is_dynamic

    img4 = res.images[3]
    assert img4.name == "eileen animated"
    assert img4.is_dynamic


def test_8_audio_statements():
    """Test 8: Extract audio references, channels, and static vs dynamic targets."""
    script = """
play music "audio/theme.ogg"
play sound "sfx/click.wav" fadein 1.0
queue music "audio/next.ogg"
play music current_bgm
"""
    res = parse_string(script)
    assert len(res.audios) == 4

    a1 = res.audios[0]
    assert a1.action == "play"
    assert a1.channel == "music"
    assert a1.target == "audio/theme.ogg"
    assert a1.kind == ReferenceKind.STATIC

    a2 = res.audios[1]
    assert a2.action == "play"
    assert a2.channel == "sound"
    assert a2.target == "sfx/click.wav"
    assert a2.kind == ReferenceKind.STATIC

    a3 = res.audios[2]
    assert a3.action == "queue"
    assert a3.channel == "music"
    assert a3.target == "audio/next.ogg"
    assert a3.kind == ReferenceKind.STATIC

    a4 = res.audios[3]
    assert a4.action == "play"
    assert a4.channel == "music"
    assert a4.target == "current_bgm"
    assert a4.kind == ReferenceKind.DYNAMIC


def test_9_define_and_default():
    """Test 9: Extract define and default declarations with optional priorities."""
    script = """
define s = Character("Sylvie")
define config.name = _("The Question")
define 10 custom_priority = True
default score = 0
default -5 book_unlocked = False
"""
    res = parse_string(script)
    assert len(res.variables) == 5

    defs = res.defines
    defaults = res.defaults
    assert len(defs) == 3
    assert len(defaults) == 2

    assert defs[0].name == "s"
    assert defs[0].raw_value == 'Character("Sylvie")'
    assert defs[0].priority is None

    assert defs[1].name == "config.name"
    assert defs[2].name == "custom_priority"
    assert defs[2].priority == 10

    assert defaults[0].name == "score"
    assert defaults[0].raw_value == "0"
    assert defaults[1].name == "book_unlocked"
    assert defaults[1].priority == -5


def test_10_translate_blocks():
    """Test 10: Extract translate blocks (strings, dialog IDs, styles)."""
    script = """
translate spanish start_915cb944:
    "Hola mundo"

translate spanish strings:
    old "Start Game"
    new "Comenzar Juego"

translate None strings:
    old "Load"
    new "Cargar"
"""
    res = parse_string(script)
    assert len(res.translations) == 3

    t1 = res.translations[0]
    assert t1.language == "spanish"
    assert t1.identifier == "start_915cb944"

    t2 = res.translations[1]
    assert t2.language == "spanish"
    assert t2.identifier == "strings"

    t3 = res.translations[2]
    assert t3.language == "None"
    assert t3.identifier == "strings"


def test_11_python_block_detection_without_execution():
    """Test 11: Detect Python blocks with start/end lines without executing code."""
    script = """
init -1 python:
    # Malicious attempt that must NOT be executed:
    import os
    variable_a = 42

label start:
    python:
        x = 10
        y = 20

    return
"""
    res = parse_string(script)
    assert len(res.python_blocks) == 2

    b1 = res.python_blocks[0]
    assert b1.block_type == "init -1 python"
    assert b1.location.line_number == 2
    assert b1.end_line == 5

    b2 = res.python_blocks[1]
    assert b2.block_type == "python"
    assert b2.location.line_number == 8
    assert b2.end_line == 10


def test_12_unicode_handling(tmp_path: Path):
    """Test 12: Ensure parser handles international UTF-8 characters seamlessly."""
    script = """
# ¡Hola, Luka!
# 日本語: こんにちは
# 中文: 你好
# Русский: Привет

define player_greeting = "¡Hola, señor Luka! こんにちは 你好 Привет"

label start_привет:
    "¡Hola! ¿Cómo estás?"
    return
"""
    file_path = tmp_path / "unicode.rpy"
    file_path.write_text(script, encoding="utf-8")

    parser = RpyParser()
    res = parser.parse_file(file_path)

    assert len(res.labels) == 1
    assert res.labels[0].name == "start_привет"
    assert len(res.defines) == 1
    assert "こんにちは" in res.defines[0].raw_value
    assert len(res.errors) == 0


def test_13_comments_not_parsed_as_statements():
    """Test 13: Statements inside comments must be ignored."""
    script = """
# jump nonexistent_label
# call fake_function
# image test_image = "missing.png"
# play music "missing.ogg"
# define bad_var = 1

label start:
    # jump another_fake
    return
"""
    res = parse_string(script)
    assert len(res.labels) == 1
    assert len(res.jumps) == 0
    assert len(res.calls) == 0
    assert len(res.images) == 0
    assert len(res.audios) == 0
    assert len(res.defines) == 0


def test_14_strings_dialogue_not_parsed_as_statements():
    """Test 14: Dialogue text mentioning statements must not be parsed."""
    script = '''
label start:
    "jump nonexistent"
    s "call missing_function"
    "image fake = 'fake.png'"
    """
    jump inside_multiline
    call inside_multiline
    """
    return
'''
    res = parse_string(script)
    assert len(res.labels) == 1
    assert len(res.jumps) == 0
    assert len(res.calls) == 0
    assert len(res.images) == 0


def test_lexer_comment_stripping_and_strings():
    """Test lexer helper directly with quotes and escape edge cases."""
    code, comment, multiline = strip_comment_and_track_strings('e "Hello # world"')
    assert code.strip() == 'e "Hello # world"'
    assert comment is None
    assert multiline is None

    code, comment, multiline = strip_comment_and_track_strings('label start: # a comment')
    assert code.strip() == 'label start:'
    assert comment == 'a comment'

    code, comment, multiline = strip_comment_and_track_strings('e "Escaped \\" and # inside"')
    assert code.strip() == 'e "Escaped \\" and # inside"'
    assert comment is None


def test_source_loader_corrupt_fallback(tmp_path: Path):
    """Test SourceLoader recovers with replacement characters on corrupt encoding."""
    corrupt_file = tmp_path / "corrupt.rpy"
    # Write invalid UTF-8 bytes (0xff 0xfe alone in non-UTF16)
    corrupt_file.write_bytes(b"label start:\n    # \xff\xfe invalid\n    return\n")

    source = SourceLoader.load(corrupt_file)
    assert source.encoding_warning is not None

    parser = RpyParser()
    res = parser.parse_source(source)
    assert len(res.labels) == 1
    assert any("invalid UTF-8 bytes" in err.message for err in res.errors)


def test_project_parser_ignores_rpyc(tmp_path: Path):
    """Test ProjectParser strictly parses .rpy/.rpym and ignores .rpyc."""
    game_dir = tmp_path / "game"
    game_dir.mkdir()

    (game_dir / "script.rpy").write_text("label start: return\n", encoding="utf-8")
    (game_dir / "script.rpyc").write_bytes(b"RENPY RPC-BINARY DATA")

    project_parser = ProjectParser()
    parsed = project_parser.parse_project(game_dir)

    assert parsed.total_files_parsed == 1
    assert "script.rpy" in parsed.files
    assert "script.rpyc" not in parsed.files


def test_15_real_project_the_question():
    """Test 15: Run parser against real SDK sample project 'the_question'."""
    workspace_root = Path(__file__).resolve().parents[2]
    the_question_dir = workspace_root / "the_question" / "game"
    assert the_question_dir.is_dir(), "the_question/game directory should exist in workspace"

    project_parser = ProjectParser()
    parsed = project_parser.parse_project(the_question_dir)

    # Validate high-level expectations on the real game
    assert parsed.total_files_parsed > 0
    assert parsed.total_files_failed == 0
    assert parsed.total_labels >= 6  # the_question has exactly 8 labels
    assert parsed.total_jumps >= 5
    assert parsed.total_translations >= 100  # translations in multiple languages
    assert parsed.total_defines >= 10


def test_project_parser_parse_files_directly(tmp_path: Path):
    """Test parse_files method with a specific list of Path objects."""
    game_dir = tmp_path / "game"
    game_dir.mkdir()
    f1 = game_dir / "story.rpy"
    f2 = game_dir / "screens.rpym"
    f3 = game_dir / "ignored.txt"

    f1.write_text("label start:\n    return\n", encoding="utf-8")
    f2.write_text("label sub:\n    return\n", encoding="utf-8")
    f3.write_text("not a script", encoding="utf-8")

    project_parser = ProjectParser()
    parsed = project_parser.parse_files([f1, f2, f3], game_directory=game_dir)

    assert parsed.total_files_parsed == 2
    assert "story.rpy" in parsed.files
    assert "screens.rpym" in parsed.files
    assert parsed.total_labels == 2


def test_project_parser_progress_callback(tmp_path: Path):
    """Test progress callback during project parsing."""
    game_dir = tmp_path / "game"
    game_dir.mkdir()
    (game_dir / "s1.rpy").write_text("label a: return\n", encoding="utf-8")
    (game_dir / "s2.rpy").write_text("label b: return\n", encoding="utf-8")

    progress_events = []

    def callback(path: str, cur: int, total: int):
        progress_events.append((path, cur, total))

    project_parser = ProjectParser()
    parsed = project_parser.parse_project(game_dir, progress_callback=callback)

    assert parsed.total_files_parsed == 2
    assert len(progress_events) == 2
    assert progress_events[0][1] == 1
    assert progress_events[0][2] == 2
    assert progress_events[1][1] == 2
    assert progress_events[1][2] == 2


def test_screen_call_and_show_with_clauses():
    """Test that transitions and clauses on screen calls and shows are cleanly stripped."""
    script = """
label test:
    call screen quest_board with fade
    call screen inventory_screen(item=1) nopredict
    show screen hud_display onlayer overlay
"""
    res = parse_string(script)
    targets = [c.target for c in res.calls if c.is_screen]
    assert targets == ["quest_board", "inventory_screen", "hud_display"]


def test_register_channel_parsing():
    """Test that renpy.music.register_channel is captured from Python blocks and $ statements."""
    script = """
init python:
    renpy.music.register_channel("sfx_loop", mixer="sfx", loop=True)
    renpy.music.register_channel("ambient", mixer="voice", loop=True)

init -1:
    $ renpy.music.register_channel("custom_voice", "voice")
"""
    res = parse_string(script)
    assert "sfx_loop" in res.registered_channels
    assert "ambient" in res.registered_channels
    assert "custom_voice" in res.registered_channels


def test_utf8_bom_file_loading(tmp_path: Path):
    """Test that files starting with UTF-8 BOM are loaded cleanly without losing line 1."""
    f = tmp_path / "bom_script.rpy"
    # Write UTF-8 BOM followed by a label
    f.write_bytes(b"\xef\xbb\xbflabel start_from_bom:\n    return\n")

    parser = RpyParser()
    res = parser.parse_file(f)
    assert len(res.labels) == 1
    assert res.labels[0].name == "start_from_bom"


def test_screen_ui_label_not_script_label():
    """Test that UI displayable 'label _(...)' inside a screen is not treated as a script label."""
    script = """
screen preferences():
    vbox:
        label _("Display"):
            text_size 20
        label _("Sound"):
            text_size 20

label real_script_label:
    return
"""
    res = parse_string(script)
    label_names = [lbl.name for lbl in res.labels]
    assert label_names == ["real_script_label"]
    assert "_" not in label_names


def test_screen_with_nested_type_hints():
    """Test screens with complex Python nested parameter lists like cards=list[Card]()):."""
    script = """
screen _combat_victory_cards(cards=list[PlayerStats, CardDef]()):
    text "Victory"
"""
    res = parse_string(script)
    assert len(res.screens) == 1
    assert res.screens[0].name == "_combat_victory_cards"


def test_named_menu_creates_label():
    """Test that named menus define a label target according to Ren'Py specification."""
    script = """
label demo_transitions:
    menu demo_transitions_menu:
        "Choice 1":
            return
    jump demo_transitions_menu
"""
    res = parse_string(script)
    label_names = [lbl.name for lbl in res.labels]
    assert "demo_transitions" in label_names
    assert "demo_transitions_menu" in label_names
    assert len(res.jumps) == 1
    assert res.jumps[0].target == "demo_transitions_menu"


def test_label_with_nested_parameter_calls():
    """Test labels with nested function call parameters such as Fade(1, 0, 1)."""
    script = """
label get_scene(cur_scene, trans=Fade(1, 0, 1)):
    return
"""
    res = parse_string(script)
    assert len(res.labels) == 1
    assert res.labels[0].name == "get_scene"
    assert "Fade(1, 0, 1)" in (res.labels[0].params or "")


def test_audio_with_playback_clauses():
    """Test that Ren'Py audio playback clauses like <from 0 to 80> are stripped from path."""
    script = """
play music "<from 0 to 80>audio/bgm/theme.ogg"
play sound "<loop 13>audio/sfx/click.ogg"
queue music "<to 2.5>audio/bgm/ending.ogg"
"""
    res = parse_string(script)
    assert len(res.audios) == 3
    assert res.audios[0].target == "audio/bgm/theme.ogg"
    assert res.audios[0].channel == "music"
    assert res.audios[1].target == "audio/sfx/click.ogg"
    assert res.audios[1].channel == "sound"
    assert res.audios[2].target == "audio/bgm/ending.ogg"
    assert res.audios[2].channel == "music"


def test_voice_statement_parsing():
    """Test that Ren'Py voice statements are parsed as audio references on 'voice' channel."""
    script = """
voice "audio/voice/line01.ogg"
voice dyn_voice_var
"""
    res = parse_string(script)
    assert len(res.audios) == 2
    assert res.audios[0].channel == "voice"
    assert res.audios[0].target == "audio/voice/line01.ogg"
    assert res.audios[0].action == "voice"
    assert res.audios[1].channel == "voice"
    assert res.audios[1].target == "dyn_voice_var"
    assert res.audios[1].is_dynamic


def test_layeredimage_statement_parsing():
    """Test that layeredimage declarations are parsed as ImageDefinitions."""
    script = """
layeredimage augustina:
    always "augustina_base"
    group outfit:
        attribute dress default
"""
    res = parse_string(script)
    assert len(res.images) == 1
    assert res.images[0].name == "augustina"
    assert not res.images[0].is_dynamic


def test_audio_list_parsing():
    """Test that audio lists in play and queue statements are extracted."""
    script = """
play music [ "intro.ogg", "<from 5>loop.ogg" ] fadeout 1.0
queue sound [ "step1.wav", "step2.wav" ]
"""
    res = parse_string(script)
    assert len(res.audios) == 4
    assert res.audios[0].target == "intro.ogg"
    assert res.audios[0].channel == "music"
    assert res.audios[1].target == "loop.ogg"
    assert res.audios[1].channel == "music"
    assert res.audios[2].target == "step1.wav"
    assert res.audios[2].channel == "sound"
    assert res.audios[3].target == "step2.wav"
    assert res.audios[3].channel == "sound"


def test_dialogue_with_escaped_quotes():
    """Test that escaped quotes in dialogue strings preserve enclosed text tags."""
    script = r'''
label start:
    "If you set {b}distribution=\"gaussian\"{/b}, then it works."
'''
    res = parse_string(script)
    assert len(res.dialogues) == 1
    assert res.dialogues[0].text == r'If you set {b}distribution=\"gaussian\"{/b}, then it works.'


def test_menu_item_with_escaped_quotes():
    """Test that choices in menus containing escaped quotes are recognized."""
    script = r'''
label start:
    menu:
        with dissolve
        "\"Which is the safe door?\" Then go through the other door.":
            $ points += 1
        "\"Ignore me if you agree to give me a blowjob\"":
            $ points += 2
        '\'Single quote choice\'':
            pass
    return
'''
    res = parse_string(script)
    assert len(res.menus) == 1
    assert res.menus[0].item_count == 3


def test_multiline_dialogue_does_not_trigger_broken_calls():
    """Test that multiline dialogue lines starting with keywords like 'call'
    are not parsed as call statements.
    """
    script = '''
label start:
    dr "And if you encounter any issues... don't hesitate to
    call for me. I'll be on this station."
    dr "Here is another line that starts with
    jump to the rescue."
    call actual_routine
    return

label actual_routine:
    return
'''
    res = parse_string(script)
    assert len(res.calls) == 1
    assert res.calls[0].target == "actual_routine"
    assert len(res.jumps) == 0


def test_multiline_quote_reset_at_top_level_label():
    """Test that an unclosed standard quote is defensively terminated at next top-level label."""
    script = '''
label start:
    "forgot closing quote
label next_label:
    call valid_target
    return
'''
    res = parse_string(script)
    assert len(res.labels) == 2
    assert [lbl.name for lbl in res.labels] == ["start", "next_label"]
    assert len(res.calls) == 1
    assert res.calls[0].target == "valid_target"


