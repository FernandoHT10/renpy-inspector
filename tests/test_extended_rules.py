"""Unit tests for Phase 6 Extended QA Rules."""

from pathlib import Path

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.models.enums import Severity
from renpy_inspector.core.models.location import Location
from renpy_inspector.core.models.project import RenPyProject
from renpy_inspector.core.parser.result import FileParseResult, ParsedProject
from renpy_inspector.core.rules.assets.invalid_audio_channel import InvalidAudioChannelRule
from renpy_inspector.core.rules.code.shadow_builtin import ShadowBuiltinRule
from renpy_inspector.core.rules.code.undefined_screen import UndefinedScreenRule
from renpy_inspector.core.rules.code.unused_label import UnusedLabelRule
from renpy_inspector.core.scanner.asset_catalog import AssetCatalog


def make_dummy_context(file_results: list[FileParseResult]) -> ProjectContext:
    proj = RenPyProject(
        name="TestGame",
        root_path=Path("/game"),
        game_path=Path("/game/game"),
    )
    parsed = ParsedProject(files={f.file_path: f for f in file_results})
    catalog = AssetCatalog()
    return ProjectContext.build(project=proj, catalog=catalog, parsed_project=parsed)


def test_unused_label_rule():
    from renpy_inspector.core.models.symbols import JumpReference, LabelSymbol

    # File 1 has start (builtin), normal_label (jumped to), and dead_label (never used)
    loc = Location(file_path="game/script.rpy", line_number=1)
    f1 = FileParseResult(
        file_path="game/script.rpy",
        labels=[
            LabelSymbol(name="start", location=loc),
            LabelSymbol(name="normal_label", location=loc),
            LabelSymbol(name="dead_branch", location=loc),
            LabelSymbol(name="_internal_helper", location=loc),
        ],
        jumps=[
            JumpReference(target="normal_label", location=loc),
        ],
    )

    ctx = make_dummy_context([f1])
    rule = UnusedLabelRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].rule_id == "RPY-CODE-005"
    assert issues[0].severity == Severity.INFO
    assert "dead_branch" in issues[0].title
    assert "dead_branch" in issues[0].message


def test_undefined_screen_rule():
    from renpy_inspector.core.models.symbols import CallReference, ScreenDefinition

    loc = Location(file_path="game/screens.rpy", line_number=1)
    f1 = FileParseResult(
        file_path="game/screens.rpy",
        screens=[
            ScreenDefinition(name="custom_ui", location=loc),
        ],
        calls=[
            CallReference(target="preferences", location=loc, is_screen=True),  # Builtin screen
            CallReference(target="custom_ui", location=loc, is_screen=True),  # Defined screen
            CallReference(target="nonexistent_screen", location=loc, is_screen=True),  # Undefined
            CallReference(target="some_label", location=loc, is_screen=False),  # Normal label call
        ],
    )

    ctx = make_dummy_context([f1])
    rule = UndefinedScreenRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].rule_id == "RPY-SCREEN-001"
    assert issues[0].severity == Severity.ERROR
    assert "nonexistent_screen" in issues[0].title


def test_invalid_audio_channel_rule():
    from renpy_inspector.core.models.symbols import AudioReference

    loc = Location(file_path="game/script.rpy", line_number=10)
    f1 = FileParseResult(
        file_path="game/script.rpy",
        audios=[
            AudioReference(channel="music", target="audio/bgm.ogg", location=loc),  # Standard
            AudioReference(channel="sound", target="audio/sfx.ogg", location=loc),  # Standard
            AudioReference(channel="musci", target="audio/typo.ogg", location=loc),  # Typo channel
        ],
    )

    ctx = make_dummy_context([f1])
    rule = InvalidAudioChannelRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].rule_id == "RPY-AUDIO-002"
    assert issues[0].severity == Severity.WARNING
    assert "musci" in issues[0].title


def test_shadow_builtin_rule():
    from renpy_inspector.core.models.symbols import VariableDeclaration

    loc = Location(file_path="game/script.rpy", line_number=5)
    f1 = FileParseResult(
        file_path="game/script.rpy",
        variables=[
            VariableDeclaration(name="config.name", kind="define", location=loc),  # Property OK
            VariableDeclaration(name="my_flag", kind="default", location=loc),  # User var OK
            VariableDeclaration(name="renpy", kind="define", location=loc),  # Dangerous shadow!
            VariableDeclaration(name="store", kind="default", location=loc),  # Dangerous shadow!
            VariableDeclaration(name="gui", kind="define", location=loc),  # Dangerous shadow!
        ],
    )

    ctx = make_dummy_context([f1])
    rule = ShadowBuiltinRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 3
    rule_ids = [i.rule_id for i in issues]
    assert all(rid == "RPY-CODE-006" for rid in rule_ids)
    names = [i.title for i in issues]
    assert any("renpy" in n for n in names)
    assert any("store" in n for n in names)
    assert any("gui" in n for n in names)
    gui_issue = next(i for i in issues if "gui" in i.title)
    assert gui_issue.severity == Severity.CRITICAL


def test_official_lifecycle_labels_and_screens_accepted():
    """Verify that official Ren'Py lifecycle hooks and screens are not flagged
    as unused or missing."""
    from renpy_inspector.core.models.symbols import CallReference, LabelSymbol

    loc = Location(file_path="game/script.rpy", line_number=1)
    f1 = FileParseResult(
        file_path="game/script.rpy",
        labels=[
            LabelSymbol(name="before_load", location=loc),
            LabelSymbol(name="after_warp", location=loc),
            LabelSymbol(name="hide_windows", location=loc),
        ],
        calls=[
            CallReference(target="skip_indicator", location=loc, is_screen=True),
            CallReference(target="bubble", location=loc, is_screen=True),
            CallReference(target="ctc", location=loc, is_screen=True),
            CallReference(target="yesno_prompt", location=loc, is_screen=True),
        ],
    )

    ctx = make_dummy_context([f1])
    label_rule = UnusedLabelRule()
    screen_rule = UndefinedScreenRule()

    assert len(label_rule.analyze(ctx)) == 0
    assert len(screen_rule.analyze(ctx)) == 0


def test_custom_registered_channel_accepted():
    """Verify that custom audio channels registered via register_channel do not produce warnings."""
    from renpy_inspector.core.models.symbols import AudioReference

    loc = Location(file_path="game/script.rpy", line_number=10)
    f1 = FileParseResult(
        file_path="game/script.rpy",
        registered_channels=["sfx_loop", "ambient"],
        audios=[
            AudioReference(channel="sfx_loop", target="audio/amb.ogg", location=loc),
            AudioReference(channel="ambient", target="audio/wind.ogg", location=loc),
            AudioReference(channel="bad_channel", target="audio/bad.ogg", location=loc),
        ],
    )

    ctx = make_dummy_context([f1])
    rule = InvalidAudioChannelRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert "bad_channel" in issues[0].title


def test_builtin_font_accepted():
    """Verify that Ren'Py engine fonts like DejaVuSans.ttf are recognized without errors."""
    from renpy_inspector.core.models.symbols import VariableDeclaration
    from renpy_inspector.core.rules.assets import MissingFontRule

    loc = Location(file_path="game/gui.rpy", line_number=65)
    f1 = FileParseResult(
        file_path="game/gui.rpy",
        variables=[
            VariableDeclaration(
                name="gui.text_font", kind="define", location=loc, raw_value='"DejaVuSans.ttf"'
            ),
            VariableDeclaration(
                name="gui.missing_font",
                kind="define",
                location=loc,
                raw_value='"custom_missing.ttf"',
            ),
        ],
    )

    ctx = make_dummy_context([f1])
    rule = MissingFontRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert "custom_missing.ttf" in issues[0].message
    assert "DejaVuSans.ttf" not in issues[0].message


def test_movie_channel_accepted():
    """Verify that playing on 'movie' channel is recognized as a standard Ren'Py channel."""
    from renpy_inspector.core.models.symbols import AudioReference

    loc = Location(file_path="game/script.rpy", line_number=10)
    f1 = FileParseResult(
        file_path="game/script.rpy",
        audios=[
            AudioReference(channel="movie", target="video/cutscene.webm", location=loc),
        ],
    )

    ctx = make_dummy_context([f1])
    rule = InvalidAudioChannelRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 0


