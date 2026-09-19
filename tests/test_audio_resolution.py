"""Unit and integration tests for AssetResolution and audio semantics."""

from pathlib import Path

import pytest

from renpy_inspector.core.models.asset import AssetInfo
from renpy_inspector.core.models.enums import AssetType, Severity
from renpy_inspector.core.models.resolution import (
    AssetResolution,
    ResolutionStatus,
    parse_audio_target,
)
from renpy_inspector.core.rules.assets.case_mismatch import CaseMismatchRule
from renpy_inspector.core.rules.assets.missing_audio import MissingAudioRule
from tests.test_rules import create_test_context


def test_parse_audio_target_clauses():
    """Clauses are cleanly stripped without corrupting paths or identifiers."""
    clauses, clean, is_q = parse_audio_target('"<loop 1.0 to 2.5>music/intro.ogg"')
    assert clauses == ("<loop 1.0 to 2.5>",)
    assert clean == "music/intro.ogg"
    assert is_q is True

    clauses, clean, is_q = parse_audio_target("<volume 0.8> <from 5.0> sfx_click")
    assert clauses == ("<volume 0.8>", "<from 5.0>")
    assert clean == "sfx_click"
    assert is_q is False


def test_asset_resolution_invariants():
    """AssetResolution dataclass enforces domain invariants in __post_init__."""
    asset = AssetInfo(
        relative_path="audio/test.ogg",
        absolute_path=Path("/tmp/audio/test.ogg"),
        asset_type=AssetType.AUDIO,
        filename="test.ogg",
        extension=".ogg",
        size_bytes=100,
    )

    # EXACT requires asset and matched_path
    with pytest.raises(ValueError, match="EXACT resolution requires non-None"):
        AssetResolution(
            status=ResolutionStatus.EXACT,
            target="audio/test.ogg",
            clean_target="audio/test.ogg",
            is_quoted=True,
            asset=None,
        )

    # AMBIGUOUS requires at least 2 candidates
    with pytest.raises(ValueError, match="AMBIGUOUS resolution requires at least 2 candidates"):
        AssetResolution(
            status=ResolutionStatus.AMBIGUOUS,
            target="ambiguous",
            clean_target="ambiguous",
            is_quoted=False,
            candidates=(asset,),
        )

    # MISSING must not have asset
    with pytest.raises(ValueError, match="MISSING resolution must not have asset"):
        AssetResolution(
            status=ResolutionStatus.MISSING,
            target="missing.ogg",
            clean_target="missing.ogg",
            is_quoted=True,
            asset=asset,
        )

    # DYNAMIC must not present candidates or asset
    with pytest.raises(ValueError, match="DYNAMIC resolution must not present candidates"):
        AssetResolution(
            status=ResolutionStatus.DYNAMIC,
            target="dyn_var",
            clean_target="dyn_var",
            is_quoted=False,
            asset=asset,
        )


def test_audio_exact_string_path_resolution(tmp_path: Path):
    """String paths resolve against game/ and game/audio/ without recursive guessing."""
    scripts = {
        "script.rpy": """
label start:
    play music "bgm/intro.ogg"
    play sound "click.wav"
    play music "audio/theme.ogg"
"""
    }
    dummy_assets = [
        "bgm/intro.ogg",
        "audio/click.wav",
        "audio/theme.ogg",
    ]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=dummy_assets)
    rule = MissingAudioRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 0


def test_audio_precedence_avoids_double_audio(tmp_path: Path):
    """A target already starting with 'audio/' does not search 'audio/audio/'."""
    scripts = {
        "script.rpy": """
label start:
    play music "audio/missing.ogg"
"""
    }
    # Place a dummy file in audio/audio/missing.ogg
    dummy_assets = ["audio/audio/missing.ogg"]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=dummy_assets)

    rule = MissingAudioRule()
    issues = rule.analyze(ctx)

    # Should be flagged as missing because "audio/missing.ogg" does not exist in game/
    assert len(issues) == 1
    assert issues[0].metadata["target"] == "audio/missing.ogg"


def test_canonical_unquoted_audio_namespace(tmp_path: Path):
    """Unquoted audio statements resolve against game/audio/ namespace."""
    scripts = {
        "script.rpy": """
label start:
    play sound click
    play music audio.theme
    play sound sfx_boom
    play sound audio.sfx.boom
"""
    }
    dummy_assets = [
        "audio/click.ogg",
        "audio/theme.opus",
        "audio/sfx/boom.wav",
    ]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=dummy_assets)
    rule = MissingAudioRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 0


def test_audio_namespace_collision_ambiguous(tmp_path: Path):
    """Colliding stems in subdirectories produce AMBIGUOUS warning."""
    scripts = {
        "script.rpy": """
label start:
    play sound click
"""
    }
    dummy_assets = [
        "audio/sfx1/click.ogg",
        "audio/sfx2/click.wav",
    ]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=dummy_assets)
    rule = MissingAudioRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].severity == Severity.WARNING
    assert "ambiguous" in issues[0].message.lower()


def test_dynamic_audio_variable_zero_false_positives(tmp_path: Path):
    """Script variables referenced in unquoted play statements are classified as DYNAMIC."""
    scripts = {
        "script.rpy": """
define selected_track = "audio/track1.ogg"
default current_sfx = "click"

label start:
    play music selected_track
    play sound current_sfx
"""
    }
    ctx = create_test_context(tmp_path, scripts, dummy_assets=[])
    rule = MissingAudioRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 0


def test_audio_case_mismatch_and_memoization(tmp_path: Path):
    """Case mismatch is cleanly reported by CaseMismatchRule and memoized across rules."""
    scripts = {
        "script.rpy": """
label start:
    play music "bgm/Theme.ogg"
"""
    }
    dummy_assets = ["bgm/theme.ogg"]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=dummy_assets)

    # MissingAudioRule does not report case mismatches (delegates to CaseMismatchRule)
    missing_rule = MissingAudioRule()
    missing_issues = missing_rule.analyze(ctx)
    assert len(missing_issues) == 0

    # CaseMismatchRule reports case mismatch
    mismatch_rule = CaseMismatchRule()
    mismatch_issues = mismatch_rule.analyze(ctx)
    assert len(mismatch_issues) == 1
    assert mismatch_issues[0].metadata["referenced"] == "bgm/Theme.ogg"
    assert mismatch_issues[0].metadata["actual"] == "bgm/theme.ogg"

    # Verify both rules received the exact same memoized resolution instance
    audio_ref = ctx.all_audios[0]
    assert audio_ref in ctx._audio_resolutions
    res = ctx._audio_resolutions[audio_ref]
    assert res.status == ResolutionStatus.CASE_MISMATCH
    assert res.matched_path == "bgm/theme.ogg"


def test_rejection_of_stem_guessing_false_negatives(tmp_path: Path):
    """A missing .wav is flagged as MISSING even if an unrelated .ogg file has the same stem."""
    scripts = {
        "script.rpy": """
label start:
    play music "bgm/battle.wav"
"""
    }
    # An unrelated .ogg file exists in a different folder
    dummy_assets = ["sfx/battle.ogg"]
    ctx = create_test_context(tmp_path, scripts, dummy_assets=dummy_assets)

    rule = MissingAudioRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].metadata["target"] == "bgm/battle.wav"
    assert issues[0].severity == Severity.ERROR
    # Verify diagnostic suggestion provides helpful context
    assert "Did you mean 'sfx/battle.ogg'?" in issues[0].suggestion
