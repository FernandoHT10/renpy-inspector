"""Unit tests for Phase 3 Rule Engine and the initial 10 core QA rules."""

from pathlib import Path

import pytest

from renpy_inspector.core.engine.context import ProjectContext
from renpy_inspector.core.engine.registry import RuleRegistry
from renpy_inspector.core.engine.runner import RuleRunner
from renpy_inspector.core.models.asset import AssetInfo
from renpy_inspector.core.models.enums import AssetType, Category, Confidence, Severity
from renpy_inspector.core.models.location import Location
from renpy_inspector.core.models.project import RenPyProject
from renpy_inspector.core.models.symbols import AudioReference
from renpy_inspector.core.parser.project_parser import ProjectParser
from renpy_inspector.core.parser.result import FileParseResult, ParsedProject
from renpy_inspector.core.rules.assets.case_mismatch import CaseMismatchRule
from renpy_inspector.core.rules.assets.missing_audio import MissingAudioRule
from renpy_inspector.core.rules.assets.missing_font import MissingFontRule
from renpy_inspector.core.rules.assets.missing_image import MissingImageRule
from renpy_inspector.core.rules.assets.unused_asset import UnusedAssetCandidateRule
from renpy_inspector.core.rules.base import BaseRule
from renpy_inspector.core.rules.code.broken_call import BrokenCallRule
from renpy_inspector.core.rules.code.broken_jump import BrokenJumpRule
from renpy_inspector.core.rules.code.conflicting_define_default import (
    ConflictingDefineDefaultRule,
)
from renpy_inspector.core.rules.code.define_persistent import DefinePersistentRule
from renpy_inspector.core.rules.code.duplicate_label import DuplicateLabelRule
from renpy_inspector.core.rules.code.duplicate_screen import DuplicateScreenRule
from renpy_inspector.core.rules.code.empty_menu import EmptyMenuRule
from renpy_inspector.core.rules.code.invalid_init_priority import (
    InvalidInitPriorityRule,
)
from renpy_inspector.core.rules.code.unclosed_text_tags import UnclosedTextTagsRule
from renpy_inspector.core.rules.code.undefined_screen import UndefinedScreenRule
from renpy_inspector.core.rules.code.unreachable_code import UnreachableCodeRule
from renpy_inspector.core.rules.code.unused_label import UnusedLabelRule
from renpy_inspector.core.rules.translation.missing_translation import (
    MissingTranslationRule,
)
from renpy_inspector.core.scanner.asset_catalog import AssetCatalog
from renpy_inspector.core.scanner.file_scanner import FileScanner


def create_test_context(
    tmp_path: Path,
    script_files: dict[str, str],
    dummy_assets: list[str] | None = None,
) -> ProjectContext:
    """Helper to build a live ProjectContext from script texts and dummy asset paths."""
    game_dir = tmp_path / "game"
    game_dir.mkdir(parents=True, exist_ok=True)

    for rel_path, content in script_files.items():
        file_path = game_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    if dummy_assets:
        for rel_asset in dummy_assets:
            asset_path = game_dir / rel_asset
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            asset_path.write_bytes(b"DUMMY_BYTES")

    scanner = FileScanner()
    catalog = scanner.scan(game_dir)

    project_parser = ProjectParser()
    parsed_proj = project_parser.parse_project(game_dir, catalog=catalog)

    proj = RenPyProject(name="TestProj", root_path=tmp_path, game_path=game_dir)
    return ProjectContext.build(project=proj, catalog=catalog, parsed_project=parsed_proj)


# 1. BrokenJumpRule Tests
def test_broken_jump_rule_detects_missing_and_ignores_dynamic(tmp_path: Path):
    scripts = {
        "script.rpy": """
label start:
    jump valid_label
    jump nonexistent_label
    jump expression dynamic_var
    jump .local_broken

label valid_label:
    jump .local_valid

label .local_valid:
    return
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = BrokenJumpRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 2
    targets = [i.metadata["target"] for i in issues]
    assert "nonexistent_label" in targets
    assert ".local_broken" in targets
    assert issues[0].severity == Severity.ERROR
    assert issues[0].category == Category.CODE


# 2. BrokenCallRule Tests
def test_broken_call_rule_detects_missing_and_ignores_screen_and_dynamic(tmp_path: Path):
    scripts = {
        "script.rpy": """
label start:
    call valid_sub
    call missing_sub
    call screen some_screen
    call expression "dynamic_" + str(1)

label valid_sub:
    return
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = BrokenCallRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].metadata["target"] == "missing_sub"
    assert issues[0].severity == Severity.ERROR


# 3. DuplicateLabelRule Tests
def test_duplicate_label_rule(tmp_path: Path):
    scripts = {
        "script1.rpy": "label start:\n    return\n",
        "script2.rpy": "label start:\n    return\n",
        "script3.rpy": "label unique_label:\n    return\n",
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = DuplicateLabelRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].metadata["label_name"] == "start"
    assert issues[0].severity == Severity.ERROR
    assert "previously defined in" in issues[0].message


def test_duplicate_label_rule_allows_local_labels_under_different_scopes(tmp_path: Path):
    scripts = {
        "script.rpy": """
label chapter1:
    jump .choice
label .choice:
    return

label chapter2:
    jump .choice
label .choice:
    return
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = DuplicateLabelRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 0  # chapter1.choice and chapter2.choice are distinct!


# 4. ConflictingDefineDefaultRule Tests
def test_conflicting_define_default_rule(tmp_path: Path):
    scripts = {
        "defs.rpy": "define score = 0\ndefine config.name = 'Test'\n",
        "state.rpy": "default score = 0\ndefault player_level = 1\n",
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = ConflictingDefineDefaultRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].metadata["variable"] == "score"
    assert issues[0].severity == Severity.WARNING


# 5. MissingAudioRule Tests
def test_missing_audio_rule(tmp_path: Path):
    scripts = {
        "script.rpy": """
label start:
    play music "bgm/intro.ogg"
    play sound "audio/click.wav"
    play music "missing_song.ogg"
    play music dynamic_audio_var
"""
    }
    assets = ["bgm/intro.ogg", "audio/click.wav"]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=assets)

    rule = MissingAudioRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].metadata["target"] == "missing_song.ogg"
    assert issues[0].severity == Severity.ERROR
    assert issues[0].category == Category.AUDIO


# 6. MissingImageRule Tests
def test_missing_image_rule(tmp_path: Path):
    scripts = {
        "script.rpy": """
image bg room = "images/room.png"
image bg missing = "images/not_found.png"
image eileen dynamic = Movie(play="vid.ogv")
"""
    }
    assets = ["images/room.png"]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=assets)

    rule = MissingImageRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].metadata["image_name"] == "bg missing"
    assert issues[0].severity == Severity.ERROR


# 7. CaseMismatchRule Tests
def test_case_mismatch_rule():
    """Test case mismatch detection using an AssetCatalog."""
    catalog = AssetCatalog([
        AssetInfo(
            relative_path="images/room.png",
            absolute_path=Path("/tmp/game/images/room.png"),
            asset_type=AssetType.IMAGE,
            filename="room.png",
            extension=".png",
            size_bytes=100,
        ),
        AssetInfo(
            relative_path="audio/theme.ogg",
            absolute_path=Path("/tmp/game/audio/theme.ogg"),
            asset_type=AssetType.AUDIO,
            filename="theme.ogg",
            extension=".ogg",
            size_bytes=500,
        ),
    ])

    proj = RenPyProject(name="Test", root_path=Path("/tmp"), game_path=Path("/tmp/game"))
    loc = Location(file_path="game/script.rpy", line_number=5)
    from renpy_inspector.core.models.symbols import ImageDefinition

    file_result = FileParseResult(
        file_path="game/script.rpy",
        images=[
            ImageDefinition(name="bg room", location=loc, asset_reference="images/ROOM.png")
        ],
        audios=[
            AudioReference(channel="music", target="audio/THEME.ogg", location=loc)
        ],
    )
    parsed_proj = ParsedProject(files={"game/script.rpy": file_result})
    ctx = ProjectContext.build(proj, catalog, parsed_proj)

    rule = CaseMismatchRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 2
    assert any(i.metadata.get("referenced") == "images/ROOM.png" for i in issues)
    assert any(i.metadata.get("referenced") == "audio/THEME.ogg" for i in issues)
    assert all(i.severity == Severity.WARNING for i in issues)
    assert all("Linux" in i.message for i in issues)


# 8. MissingFontRule Tests
def test_missing_font_rule(tmp_path: Path):
    scripts = {
        "gui.rpy": """
define gui.text_font = "DejaVuSans.ttf"
define gui.missing_font = "NotHere.ttf"
"""
    }
    assets = ["fonts/DejaVuSans.ttf"]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=assets)

    rule = MissingFontRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].metadata["font_path"] == "NotHere.ttf"
    assert issues[0].severity == Severity.ERROR


# 9. MissingTranslationRule Tests
def test_missing_translation_rule(tmp_path: Path):
    scripts = {
        "tl/spanish/script.rpy": """
translate spanish start_111:
    "Hola"
translate spanish right_222:
    "Adios"
""",
        "tl/french/script.rpy": """
translate french start_111:
    "Bonjour"
# Missing right_222 in french!
""",
    }
    ctx = create_test_context(tmp_path, scripts)

    rule = MissingTranslationRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].metadata["language"] == "french"
    assert issues[0].metadata["missing_identifier"] == "right_222"
    assert issues[0].severity == Severity.WARNING


# 10. UnusedAssetCandidateRule Tests
def test_unused_asset_candidate_rule(tmp_path: Path):
    scripts = {
        "script.rpy": """
label start:
    play music "theme.ogg"
    return
"""
    }
    assets = ["audio/theme.ogg", "images/unreferenced_bg.png"]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=assets)

    rule = UnusedAssetCandidateRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].metadata["filename"] == "unreferenced_bg.png"
    assert issues[0].severity == Severity.INFO
    assert issues[0].confidence == Confidence.SUSPECTED


# 11. RuleRunner and RuleRegistry Tests
def test_rule_runner_and_registry(tmp_path: Path):
    scripts = {
        "script.rpy": """
label start:
    jump missing_dest
"""
    }
    ctx = create_test_context(tmp_path, scripts)

    registry = RuleRegistry.create_default()
    assert len(registry.get_all_rules()) == 20

    # Test disabling BrokenJumpRule
    registry.set_enabled("RPY-CODE-001", False)
    runner = RuleRunner(registry=registry)
    result = runner.run(ctx)
    assert not any(i.rule_id == "RPY-CODE-001" for i in result.issues)
    assert result.is_complete
    assert not result.has_failures
    assert isinstance(result.issues, tuple)
    assert isinstance(result.failures, tuple)

    # Re-enable
    registry.set_enabled("RPY-CODE-001", True)
    progress_reported = []

    def progress(title, idx, total):
        progress_reported.append((title, idx, total))

    result2 = runner.run(ctx, progress_callback=progress)
    assert any(i.rule_id == "RPY-CODE-001" for i in result2.issues)
    assert len(progress_reported) == len(registry.get_all_rules())
    assert result2.is_complete
    assert not result2.has_failures


class CrashingRule(BaseRule):
    """Test rule that raises an unhandled exception during analyze()."""

    rule_id = "TEST-CRASH-001"
    title = "Crashing Test Rule"
    category = Category.CODE
    default_severity = Severity.ERROR
    description = "A rule that crashes intentionally for testing."

    def analyze(self, context):
        raise RuntimeError("Simulated rule crash!")


class GeneratorCrashingRule(BaseRule):
    """Test rule that raises an unhandled exception during generator iteration."""

    rule_id = "TEST-GEN-CRASH-001"
    title = "Generator Crashing Rule"
    category = Category.CODE
    default_severity = Severity.ERROR
    description = "A rule that crashes midway through generator iteration."

    def analyze(self, context):
        yield self.create_issue(
            message="First valid issue before crash",
            location=Location("test.rpy", 1),
            suggestion="Fix it",
        )
        raise ValueError("Crash during generator iteration!")


class RuleWithoutIdOrTitle:
    """Test rule that omits rule_id and title attributes."""

    category = Category.CODE
    default_severity = Severity.ERROR

    def analyze(self, context):
        raise TypeError("Crash from rule without id or title")


def test_rule_runner_records_rule_failure(tmp_path: Path):
    """RuleRunner must catch exceptions, record RuleFailure, and continue running other rules."""
    scripts = {"script.rpy": "label start:\n    return\n"}
    ctx = create_test_context(tmp_path, scripts)

    registry = RuleRegistry()
    registry.register(CrashingRule())
    registry.register(BrokenJumpRule())

    runner = RuleRunner(registry=registry)
    result = runner.run(ctx)

    assert result.has_failures
    assert not result.is_complete
    assert len(result.failures) == 1
    assert result.total_rules_count == 2
    assert result.executed_rules_count == 1  # BrokenJumpRule executed

    failure = result.failures[0]
    assert failure.rule_id == "TEST-CRASH-001"
    assert failure.rule_title == "Crashing Test Rule"
    assert failure.error_type == "RuntimeError"
    assert "Simulated rule crash!" in failure.error_message
    assert "RuntimeError" in failure.traceback
    assert isinstance(result.issues, tuple)
    assert isinstance(result.failures, tuple)


def test_rule_runner_failure_during_generator_iteration(tmp_path: Path):
    """If a rule returns a generator that crashes during iteration, it must record failure."""
    scripts = {"script.rpy": "label start:\n    return\n"}
    ctx = create_test_context(tmp_path, scripts)

    registry = RuleRegistry()
    registry.register(GeneratorCrashingRule())

    runner = RuleRunner(registry=registry)
    result = runner.run(ctx)

    assert result.has_failures
    assert not result.is_complete
    assert result.executed_rules_count == 0  # Did not complete iteration successfully
    assert len(result.failures) == 1
    assert result.failures[0].error_type == "ValueError"
    assert "Crash during generator iteration!" in result.failures[0].error_message


def test_rule_runner_fail_fast_reraises(tmp_path: Path):
    """With fail_fast=True, RuleRunner must immediately re-raise the unhandled exception."""
    scripts = {"script.rpy": "label start:\n    return\n"}
    ctx = create_test_context(tmp_path, scripts)

    registry = RuleRegistry()
    registry.register(CrashingRule())

    runner = RuleRunner(registry=registry)
    with pytest.raises(RuntimeError, match="Simulated rule crash!"):
        runner.run(ctx, fail_fast=True)


def test_rule_runner_base_exceptions_propagate(tmp_path: Path):
    """BaseExceptions such as KeyboardInterrupt must not be intercepted by RuleRunner."""
    scripts = {"script.rpy": "label start:\n    return\n"}
    ctx = create_test_context(tmp_path, scripts)

    class KeyboardInterruptRule(BaseRule):
        rule_id = "TEST-INT-001"
        title = "Interrupt Rule"
        category = Category.CODE
        default_severity = Severity.ERROR
        description = "Raises KeyboardInterrupt."

        def analyze(self, context):
            raise KeyboardInterrupt("Simulated user interrupt")

    registry = RuleRegistry()
    registry.register(KeyboardInterruptRule())

    runner = RuleRunner(registry=registry)
    with pytest.raises(KeyboardInterrupt):
        runner.run(ctx)


def test_rule_without_id_or_title_uses_class_fallback(tmp_path: Path):
    """Rules omitting rule_id or title must fallback to rule.__class__.__name__ without error."""
    scripts = {"script.rpy": "label start:\n    return\n"}
    ctx = create_test_context(tmp_path, scripts)

    registry = RuleRegistry()
    registry.register(RuleWithoutIdOrTitle())  # type: ignore

    runner = RuleRunner(registry=registry)
    result = runner.run(ctx)

    assert result.has_failures
    assert result.failures[0].rule_id == "RuleWithoutIdOrTitle"
    assert result.failures[0].rule_title == "RuleWithoutIdOrTitle"
    assert result.failures[0].error_type == "TypeError"


def test_unused_asset_candidate_rule_skipped_when_no_scripts(tmp_path: Path):
    """When a project has 0 parsed scripts (compiled-only), do not emit unused asset warnings."""
    game_dir = tmp_path / "game"
    game_dir.mkdir(parents=True)
    asset_img = AssetInfo(
        relative_path="images/bg.png",
        absolute_path=game_dir / "images" / "bg.png",
        asset_type=AssetType.IMAGE,
        filename="bg.png",
        extension=".png",
        size_bytes=5000,
    )
    catalog = AssetCatalog([asset_img])
    project = RenPyProject(name="CompiledOnly", root_path=tmp_path, game_path=game_dir)
    parsed = ParsedProject(files={})  # 0 parsed scripts

    ctx = ProjectContext.build(project=project, catalog=catalog, parsed_project=parsed)
    rule = UnusedAssetCandidateRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 0

    # Also skipped if only translation/module stubs (.rpym) exist without .rpy source files
    file_result = FileParseResult(file_path="game/tl/None/common.rpym")
    parsed_rpym = ParsedProject(files={"game/tl/None/common.rpym": file_result})
    ctx_rpym = ProjectContext.build(project=project, catalog=catalog, parsed_project=parsed_rpym)
    issues_rpym = rule.analyze(ctx_rpym)
    assert len(issues_rpym) == 0


def test_missing_audio_rule_with_playback_clauses(tmp_path: Path):
    """Audio references with <from 0 to 80> clauses must resolve without false positives."""
    game_dir = tmp_path / "game"
    game_dir.mkdir(parents=True)
    audio_dir = game_dir / "audio"
    audio_dir.mkdir()
    (audio_dir / "intro.ogg").write_bytes(b"OGG_HEADER")

    asset_audio = AssetInfo(
        relative_path="audio/intro.ogg",
        absolute_path=audio_dir / "intro.ogg",
        asset_type=AssetType.AUDIO,
        filename="intro.ogg",
        extension=".ogg",
        size_bytes=10,
    )
    catalog = AssetCatalog([asset_audio])
    project = RenPyProject(name="AudioTest", root_path=tmp_path, game_path=game_dir)

    loc = Location(file_path="game/script.rpy", line_number=10)
    ref = AudioReference(
        channel="music",
        target="<from 0 to 80>audio/intro.ogg",
        action="play",
        location=loc,
    )
    file_result = FileParseResult(file_path="game/script.rpy", audios=[ref])
    parsed = ParsedProject(files={"game/script.rpy": file_result})

    ctx = ProjectContext.build(project=project, catalog=catalog, parsed_project=parsed)
    rule = MissingAudioRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 0


def test_unreachable_code_rule(tmp_path: Path):
    scripts = {
        "story.rpy": """
label start:
    jump epilogue
    "This dialogue is unreachable!"
    $ dead_var = 1

label epilogue:
    return
    $ also_dead = 2

label normal_flow:
    jump start
label next_label:
    "This label is reachable!"
    return
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = UnreachableCodeRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 2
    assert all(i.rule_id == "RPY-CODE-007" for i in issues)
    assert issues[0].metadata["preceding_statement"] == "jump epilogue"
    assert issues[1].metadata["preceding_statement"] == "return"


def test_define_persistent_rule(tmp_path: Path):
    scripts = {
        "options.rpy": """
define persistent.unlocked_art = True
define store.persistent.high_score = 9999
default persistent.player_choice = "A"
define config.name = "My Visual Novel"
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = DefinePersistentRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 2
    assert all(i.rule_id == "RPY-CODE-008" for i in issues)
    vars_flagged = {i.metadata["variable"] for i in issues}
    assert vars_flagged == {"persistent.unlocked_art", "store.persistent.high_score"}


def test_empty_menu_rule(tmp_path: Path):
    scripts = {
        "menus.rpy": """
label choices:
    menu:
        "Option 1":
            jump opt1
        "Option 2":
            jump opt2

    menu:
        pass

    menu empty_named:
        $ some_code = 1
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = EmptyMenuRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 2
    assert all(i.rule_id == "RPY-CODE-009" for i in issues)


def test_duplicate_screen_rule(tmp_path: Path):
    scripts = {
        "screens.rpy": """
screen main_menu():
    text "Main Menu V1"

screen main_menu():
    text "Main Menu V2 Duplicate"

screen quick_menu():
    text "Desktop Quick Menu"

screen quick_menu():
    variant "touch"
    text "Touch Quick Menu Variant"
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = DuplicateScreenRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 1
    assert issues[0].rule_id == "RPY-SCREEN-002"
    assert issues[0].metadata["screen_name"] == "main_menu"


def test_unclosed_text_tags_rule(tmp_path: Path):
    scripts = {
        "dialogue.rpy": """
label start:
    "Hello {b}world!"
    "Welcome {color=#ff0000}{i}Hero{/i}{/color}"
    "Broken {size=30}large text without closing"
    "Wait for me...{w=1.0}{p} Ready!"
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = UnclosedTextTagsRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 2
    assert all(i.rule_id == "RPY-TEXT-001" for i in issues)
    tags_found = [i.metadata["unclosed_tags"] for i in issues]
    assert ["b"] in tags_found
    assert ["size"] in tags_found


def test_screen_action_in_undefined_screen_rule(tmp_path: Path):
    scripts = {
        "screens_test.rpy": """
label start:
    call screen missing_screen_a
    show screen missing_screen_b
    hide screen missing_screen_c
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = UndefinedScreenRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 3
    a = next(i for i in issues if "missing_screen_a" in i.title)
    b = next(i for i in issues if "missing_screen_b" in i.title)
    c = next(i for i in issues if "missing_screen_c" in i.title)
    assert a.severity == Severity.ERROR
    assert b.severity == Severity.ERROR
    assert c.severity == Severity.WARNING
    assert "via 'call screen'" in a.message
    assert "via 'show screen'" in b.message
    assert "via 'hide screen'" in c.message


def test_custom_text_tags_dynamic_rule(tmp_path: Path):
    scripts = {
        "kinetic.rpy": """
init python:
    config.custom_text_tags["bounce"] = None
    config.self_closing_custom_text_tags["tagbr"] = None

label start:
    "Text with {bounce}bouncing{/bounce} effect."
    "Text with {bounce}broken bouncing tag without close."
    "Self closing {tagbr} works without tag closure."
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    assert "bounce" in ctx.custom_text_tags
    assert "tagbr" in ctx.custom_self_closing_text_tags

    rule = UnclosedTextTagsRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 1
    assert issues[0].rule_id == "RPY-TEXT-001"
    assert issues[0].metadata["unclosed_tags"] == ["bounce"]


def test_invalid_init_priority_rule(tmp_path: Path):
    scripts = {
        "inits.rpy": """
init -1000:
    transform t1:
        pass

init 1434:
    pass

init -9999 python:
    pass

init offset = -1005

define 1200 special_flag = True

# Valid priorities should NOT produce issues
init -999:
    pass

init 999 python:
    pass

init offset = -2

define 100 safe_flag = False
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = InvalidInitPriorityRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 5
    assert all(i.rule_id == "RPY-CODE-010" for i in issues)
    priorities_flagged = [i.metadata["priority"] for i in issues]
    assert -1000 in priorities_flagged
    assert 1434 in priorities_flagged
    assert -9999 in priorities_flagged
    assert -1005 in priorities_flagged
    assert 1200 in priorities_flagged


def test_screen_action_jump_and_call_resolution(tmp_path: Path):
    scripts = {
        "screens.rpy": """
screen main_menu_custom():
    textbutton "Start Story" action Jump("prologue")
    textbutton "Tutorial" action Call("intro_tutorial")
    button action [SetVariable("x", 1), Jump("broken_target")]
""",
        "story.rpy": """
label prologue:
    "Welcome to the game."
    return

label intro_tutorial:
    "This is the tutorial."
    return

label unused_story:
    "This is unreferenced."
    return
""",
    }
    ctx = create_test_context(tmp_path, scripts)

    # 1. Broken Jump should detect broken_target from inside button action
    jump_rule = BrokenJumpRule()
    jump_issues = jump_rule.analyze(ctx)
    assert len(jump_issues) == 1
    assert jump_issues[0].metadata["target"] == "broken_target"

    # 2. Unused Label should see prologue and intro_tutorial as used, but flag unused_story
    unused_rule = UnusedLabelRule()
    unused_issues = unused_rule.analyze(ctx)
    unused_names = [i.title for i in unused_issues]
    assert "Unused Label 'unused_story'" in unused_names
    assert not any("prologue" in name for name in unused_names)
    assert not any("intro_tutorial" in name for name in unused_names)


def test_audio_namespace_and_subdirectory_resolution(tmp_path: Path):
    scripts = {
        "audio_test.rpy": """
label start:
    play sound cum_01
    play music bgm_forest
    play music "bgm/nature/bgm_forest.ogg"
    play sound "missing_sfx"
"""
    }
    dummy_assets = [
        "audio/sound/lewd/cum/cum_01.ogg",
        "audio/bgm/nature/bgm_forest.ogg",
    ]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=dummy_assets)
    rule = MissingAudioRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].metadata["target"] == "missing_sfx"


def test_subfolder_image_alias_resolution(tmp_path: Path):
    scripts = {
        "sprites.rpy": """
image musatobi = "musatobi musatobi_c1"
image wanda = "wanda c1 wanda_c1"
image missing_char = "missing unknown_c1"
"""
    }
    dummy_assets = [
        "images/characters/musatobi/musatobi_c1.webp",
        "images/characters/wanda/c1/wanda_c1.webp",
    ]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=dummy_assets)
    rule = MissingImageRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].metadata["image_name"] == "missing_char"


def test_menu_item_with_arguments_not_empty(tmp_path: Path):
    scripts = {
        "menu_test.rpy": """
label start:
    menu hahari_brothel_menu:
        "Sex"(sensitive=hahari_date == True):
            jump hahari_brothel_sex
        "Peeks" (sensitive=hahari_chat >= 25):
            jump hahari_brothel_peeks
        "Back":
            return
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = EmptyMenuRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 0


def test_inline_named_menu_not_flagged_unused(tmp_path: Path):
    scripts = {
        "story.rpy": """
label start:
    "Dialogue before choice."
    menu inline_choice_menu:
        "Yes":
            "You said yes."
        "No":
            "You said no."
    return

label real_unused_label:
    "This is actually unused."
    return
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = UnusedLabelRule()
    issues = rule.analyze(ctx)
    unused_names = [i.title for i in issues]
    assert "Unused Label 'real_unused_label'" in unused_names
    assert not any("inline_choice_menu" in name for name in unused_names)


def test_multiline_screen_signature_parsed(tmp_path: Path):
    scripts = {
        "multiline_ui.rpy": """
screen minigame_crafting_ui(
    var_typ="cooking",
    var_crf=["hero"],
    show_prep=True,
):
    default started = True
    text "Crafting..."

label start:
    call screen minigame_crafting_ui
    return
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    assert "minigame_crafting_ui" in ctx.defined_screens

    rule = UndefinedScreenRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 0


def test_template_language_excluded_from_missing_translation(tmp_path: Path):
    scripts = {
        "story.rpy": """
label start:
    "Welcome to the game."
""",
        "tl/es/story.rpy": """
translate es start_12345678:
    "Bienvenido al juego."
""",
        "tl/YourLanguage/story.rpy": """
# Empty template placeholder for community translators
""",
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = MissingTranslationRule()
    issues = rule.analyze(ctx)
    assert not any(i.metadata.get("language") == "YourLanguage" for i in issues)


def test_prefix_formatting_tags_auto_close(tmp_path: Path):
    scripts = {
        "script.rpy": """
label start:
    "{b}This is bold."
    "{size=50}Large heading"
    "{i}*sigh*"
    "{color=#ff0000}{size=30}Combined prefix tags"
    "\\\\n{color=#ffffff}Escaped newline with prefix tag"
    "Hello {b}world!"
    "Normal text {size=30}unclosed size tag"
    "{b}bold{b}"
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = UnclosedTextTagsRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 3
    tags_found = [i.metadata["unclosed_tags"] for i in issues]
    assert ["b"] in tags_found
    assert ["size"] in tags_found


def test_screen_and_tl_old_new_not_treated_as_dialogue(tmp_path: Path):
    scripts = {
        "screens.rpy": """
screen navigation():
    text _("{size=30}Main Menu")
    textbutton _("{size=-2}Preferences") action ShowMenu("preferences")
""",
        "tl/es/screens.rpy": """
translate es strings:
    old "{size=30}Main Menu"
    new "{size=30}Menú Principal"
""",
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = UnclosedTextTagsRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 0


def test_asset_token_pool_includes_screen_and_python_literals(tmp_path: Path):
    scripts = {
        "screens.rpy": """
screen my_ui():
    add "gui/circle_qte.png"
    imagebutton idle "itch-io.png" hover "itch-io-hover.png"
""",
        "logic.rpy": """
init python:
    gallery_items = ["cg/u6f1007a.webp", "special_reward.png"]
""",
    }
    assets = [
        "images/gui/circle_qte.png",
        "images/itch-io.png",
        "images/itch-io-hover.png",
        "images/cg/u6f1007a.webp",
        "images/special_reward.png",
        "images/truly_unused_cutscene.png",
    ]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=assets)
    rule = UnusedAssetCandidateRule()
    issues = rule.analyze(ctx)
    # Only truly_unused_cutscene.png should be flagged
    assert len(issues) == 1
    assert "truly_unused_cutscene.png" in issues[0].message


def test_escaped_braces_in_text_tags(tmp_path: Path):
    scripts = {
        "script.rpy": """
label start:
    "Sometimes using {{b} tag looks different than {b}bold{/b}."
    "A literal brace {{color=#fff} is not a tag."
    "Formula with braces {{x + 1}} works fine."
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = UnclosedTextTagsRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 0


def test_missing_translation_large_capping(tmp_path: Path):
    # Simulate 30 missing dialogue IDs in french
    scripts = {
        "tl/spanish/script.rpy": "\n".join(
            f"translate spanish line_{i:03d}:\n    'Texto {i}'"
            for i in range(30)
        ),
        "tl/french/script.rpy": "translate french line_000:\n    'Texte 0'",
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = MissingTranslationRule()
    issues = rule.analyze(ctx)
    # 25 detailed issues + 1 summary issue = 26
    assert len(issues) == 26
    summary = [i for i in issues if "detailed above" in i.message]
    assert len(summary) == 1
    assert summary[0].metadata.get("total_missing") == 29



