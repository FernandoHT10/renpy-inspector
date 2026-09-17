"""Unit tests for Phase 3 Rule Engine and the initial 10 core QA rules."""

from pathlib import Path

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
from renpy_inspector.core.rules.code.broken_call import BrokenCallRule
from renpy_inspector.core.rules.code.broken_jump import BrokenJumpRule
from renpy_inspector.core.rules.code.conflicting_define_default import (
    ConflictingDefineDefaultRule,
)
from renpy_inspector.core.rules.code.duplicate_label import DuplicateLabelRule
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
    parser = ProjectParser()
    parsed_proj = parser.parse_files([], Path("/tmp/game"))

    ctx = ProjectContext.build(proj, catalog, parsed_proj)

    # Inject mismatched references
    from renpy_inspector.core.models.location import Location
    from renpy_inspector.core.models.symbols import AudioReference, ImageDefinition

    loc = Location(file_path="game/script.rpy", line_number=5)
    ctx.all_images.append(
        ImageDefinition(name="bg room", location=loc, asset_reference="images/ROOM.png")
    )
    ctx.all_audios.append(
        AudioReference(channel="music", target="audio/THEME.ogg", location=loc)
    )

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
    assert len(registry.get_all_rules()) == 14

    # Test disabling BrokenJumpRule
    registry.set_enabled("RPY-CODE-001", False)
    runner = RuleRunner(registry=registry)
    issues = runner.run(ctx)
    assert not any(i.rule_id == "RPY-CODE-001" for i in issues)

    # Re-enable
    registry.set_enabled("RPY-CODE-001", True)
    progress_reported = []

    def progress(title, idx, total):
        progress_reported.append((title, idx, total))

    issues2 = runner.run(ctx, progress_callback=progress)
    assert any(i.rule_id == "RPY-CODE-001" for i in issues2)
    assert len(progress_reported) == len(registry.get_all_rules())


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

