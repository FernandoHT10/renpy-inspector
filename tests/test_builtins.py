"""Unit and integration tests for built-ins, lifecycle hooks, and screen resolution."""

from pathlib import Path

from renpy_inspector.core.models.enums import Severity
from renpy_inspector.core.rules.code.broken_jump import BrokenJumpRule
from renpy_inspector.core.rules.code.undefined_screen import UndefinedScreenRule
from renpy_inspector.core.rules.code.unused_label import UnusedLabelRule
from tests.test_rules import create_test_context


def test_missing_start_label_flagged_by_broken_jump(tmp_path: Path):
    """Jumping to 'start' when label start is missing from scripts is flagged as broken."""
    scripts = {
        "script.rpy": """
label intro:
    jump start
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    assert "start" not in ctx.defined_labels
    assert ctx.has_label("start") is False

    rule = BrokenJumpRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 1
    assert issues[0].metadata["target"] == "start"
    assert issues[0].severity == Severity.ERROR
    assert "start" in issues[0].message


def test_defined_start_label_accepted(tmp_path: Path):
    """Jumping to 'start' when label start is defined succeeds with zero issues."""
    scripts = {
        "script.rpy": """
label intro:
    jump start

label start:
    return
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    assert "start" in ctx.defined_labels
    assert ctx.has_label("start") is True

    rule = BrokenJumpRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 0


def test_lifecycle_hook_labels_not_flagged_as_unused(tmp_path: Path):
    """Defining official engine lifecycle hooks is not flagged as unused code."""
    scripts = {
        "script.rpy": """
label start:
    return

label splashscreen:
    return

label after_load:
    return
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = UnusedLabelRule()
    issues = rule.analyze(ctx)

    # splashscreen, after_load, start are in lifecycle_hook_labels -> not flagged
    assert len(issues) == 0


def test_undefined_template_screen_flagged(tmp_path: Path):
    """Referencing template screens without declaring them is flagged as undefined screen."""
    scripts = {
        "script.rpy": """
label start:
    call screen about
    show screen navigation
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = UndefinedScreenRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 2
    targets = [i.title for i in issues]
    assert any("about" in t for t in targets)
    assert any("navigation" in t for t in targets)


def test_defined_template_screen_accepted(tmp_path: Path):
    """Template screens defined in screens.rpy succeed with zero issues."""
    scripts = {
        "script.rpy": """
label start:
    call screen about
""",
        "screens.rpy": """
screen about():
    text "About this game"
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    assert "about" in ctx.defined_screens

    rule = UndefinedScreenRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 0


def test_engine_common_screens_accepted(tmp_path: Path):
    """True engine common screens from renpy/common/ are recognized as valid."""
    scripts = {
        "script.rpy": """
label start:
    call screen bubble
    show screen skip_indicator
    call screen ctc
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    rule = UndefinedScreenRule()
    issues = rule.analyze(ctx)

    assert len(issues) == 0
