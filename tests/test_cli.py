"""Tests for CLI interface."""

from pathlib import Path

from renpy_inspector.cli.main import main


def test_cli_valid_project(valid_minimal_project_dir: Path, capsys):
    """CLI should return 0 and display asset counts for a valid project."""
    exit_code = main([str(valid_minimal_project_dir)])
    captured = capsys.readouterr().out

    assert exit_code == 0
    assert "Ren'Py Inspector" in captured
    assert "Status: VALID" in captured
    assert "Scripts: 2" in captured  # script.rpy and options.rpy
    assert "Images: 1" in captured   # bg_room.png
    assert "Audio: 1" in captured    # theme.ogg
    assert "Fonts: 1" in captured    # font.ttf
    assert "Total files: 5" in captured
    assert "Inspection Results:" in captured
    assert "Problems found:" in captured
    assert "Scan and QA inspection completed successfully." in captured


def test_cli_invalid_project(tmp_path: Path, capsys):
    """CLI should return 1 and report an error for an invalid directory."""
    nonexistent = tmp_path / "nowhere"
    exit_code = main([str(nonexistent)])
    captured = capsys.readouterr().out

    assert exit_code == 1
    assert "Ren'Py Inspector" in captured
    assert "Status: INVALID" in captured
    assert "Errors:" in captured
