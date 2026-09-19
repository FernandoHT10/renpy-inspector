"""Tests for Problem #7: Nested Menus and Structural Choice Counting."""

from pathlib import Path

from renpy_inspector.core.models.enums import Severity
from renpy_inspector.core.parser.rpy_parser import RpyParser
from renpy_inspector.core.parser.source import SourceFile
from renpy_inspector.core.rules.code.empty_menu import EmptyMenuRule
from tests.test_rules import create_test_context


def parse_string(script_content: str, file_path: str = "game/script.rpy"):
    """Helper to parse a script snippet directly with RpyParser."""
    lines = tuple(script_content.splitlines())
    source = SourceFile(file_path=file_path, lines=lines, content=script_content, encoding="utf-8")
    parser = RpyParser()
    return parser.parse_source(source)


def test_1_nested_menus_independent_counting():
    """An inner menu inside a choice must not finalize the outer menu prematurely."""
    script = """
label start:
    menu:
        "Outer Choice 1":
            menu:
                "Inner Choice 1.1":
                    jump end
                "Inner Choice 1.2":
                    jump end
        "Outer Choice 2":
            jump end

label end:
    return
"""
    res = parse_string(script)
    assert len(res.menus) == 2, f"Expected 2 menus, found: {len(res.menus)}"

    # Inner menu is finalized first
    inner_menu = res.menus[0]
    outer_menu = res.menus[1]

    assert inner_menu.item_count == 2
    assert inner_menu.location.line_number == 5

    assert outer_menu.item_count == 2
    assert outer_menu.location.line_number == 3


def test_2_blank_lines_and_comments_do_not_close_menu():
    """Blank lines, comment-only lines, and multiline formatting must not close menus."""
    script = """
label start:
    menu:

        # Comment before first choice
        "Choice 1":
            $ do_something()

        # Comment between choices

        "Choice 2":
            jump next_label

        # Trailing comment
"""
    res = parse_string(script)
    assert len(res.menus) == 1
    assert res.menus[0].item_count == 2
    assert res.menus[0].location.line_number == 3


def test_3_statements_inside_choice_not_counted_as_items():
    """Statements, say/narrative lines, or indented code must not be counted as menu items."""
    script = """
label start:
    menu:
        "What should we do?":
            e "Dialogue line inside choice."
            "Another say statement."
            $ counter += 1
            call helper
            jump next

        "Second choice":
            pass
"""
    res = parse_string(script)
    assert len(res.menus) == 1
    assert res.menus[0].item_count == 2


def test_4_empty_outer_menu_detected(tmp_path: Path):
    """An empty outer menu statement is correctly flagged by EmptyMenuRule."""
    scripts = {
        "script.rpy": """
label start:
    menu:
        $ x = 1
        jump elsewhere
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    assert len(ctx.all_menus) == 1
    assert ctx.all_menus[0].item_count == 0

    rule = EmptyMenuRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 1
    assert issues[0].severity == Severity.ERROR
    assert "does not contain any selectable choice items" in issues[0].message


def test_5_empty_inner_menu_detected(tmp_path: Path):
    """An empty inner menu inside a valid outer menu is flagged without affecting the outer menu."""
    scripts = {
        "script.rpy": """
label start:
    menu:
        "Valid Option 1":
            menu:
                # Empty inner menu!
                jump end
        "Valid Option 2":
            jump end

label end:
    return
"""
    }
    ctx = create_test_context(tmp_path, scripts)
    assert len(ctx.all_menus) == 2

    # Verify counts
    inner_menu = next(m for m in ctx.all_menus if m.location.line_number == 5)
    outer_menu = next(m for m in ctx.all_menus if m.location.line_number == 3)

    assert inner_menu.item_count == 0
    assert outer_menu.item_count == 2

    rule = EmptyMenuRule()
    issues = rule.analyze(ctx)
    assert len(issues) == 1
    assert issues[0].location.line_number == 5


def test_6_three_level_nested_menus():
    """Three levels of menu nesting must all be extracted with exact independent item counts."""
    script = """
label start:
    menu:
        "Level 1 - Choice A":
            menu:
                "Level 2 - Choice A":
                    menu:
                        "Level 3 - Choice A":
                            jump end
                        "Level 3 - Choice B":
                            jump end
                        "Level 3 - Choice C":
                            jump end
                "Level 2 - Choice B":
                    jump end
        "Level 1 - Choice B":
            jump end
"""
    res = parse_string(script)
    assert len(res.menus) == 3

    # innermmost level 3
    m3 = next(m for m in res.menus if m.location.line_number == 7)
    assert m3.item_count == 3

    # middle level 2
    m2 = next(m for m in res.menus if m.location.line_number == 5)
    assert m2.item_count == 2

    # outer level 1
    m1 = next(m for m in res.menus if m.location.line_number == 3)
    assert m1.item_count == 2
