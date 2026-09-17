"""Tests for ProjectValidator logic and edge cases."""

from pathlib import Path

from renpy_inspector.core.scanner.validator import ProjectValidator


def test_validator_nonexistent_directory(tmp_path: Path):
    """Path that does not exist on the filesystem must return is_valid=False."""
    target = tmp_path / "does_not_exist"
    res = ProjectValidator.validate(target)
    assert not res.is_valid
    assert any("does not exist" in err.lower() for err in res.errors)


def test_validator_file_instead_of_directory(tmp_path: Path):
    """File path instead of directory must return is_valid=False."""
    target_file = tmp_path / "single_file.txt"
    target_file.write_text("not a dir", encoding="utf-8")
    res = ProjectValidator.validate(target_file)
    assert not res.is_valid
    assert any("not a directory" in err.lower() for err in res.errors)


def test_validator_empty_directory(tmp_path: Path):
    """Empty directory without game/ folder must return is_valid=False."""
    empty_dir = tmp_path / "empty_project"
    empty_dir.mkdir()
    res = ProjectValidator.validate(empty_dir)
    assert not res.is_valid
    assert any("game/" in err for err in res.errors)


def test_validator_game_dir_empty_no_scripts(tmp_path: Path):
    """Directory with game/ but no .rpy/.rpyc files must return is_valid=False."""
    project_dir = tmp_path / "project_no_scripts"
    game_dir = project_dir / "game"
    game_dir.mkdir(parents=True)

    # Put a random non-Ren'Py file inside game/
    (game_dir / "readme.txt").write_text("just text", encoding="utf-8")

    res = ProjectValidator.validate(project_dir)
    assert not res.is_valid
    assert any("contains no ren'py script files" in err.lower() for err in res.errors)


def test_validator_minimal_valid_fixture(valid_minimal_project_dir: Path):
    """Valid minimal project fixture must return is_valid=True."""
    res = ProjectValidator.validate(valid_minimal_project_dir)
    assert res.is_valid
    assert len(res.errors) == 0
    assert res.game_path is not None
    assert res.game_path.name == "game"
    assert "script.rpy" in res.detected_markers
    assert "options.rpy" in res.detected_markers


def test_validator_missing_optional_files_still_valid(tmp_path: Path):
    """Project with only custom_story.rpy (no options.rpy or script.rpy) is still valid."""
    project_dir = tmp_path / "custom_project"
    game_dir = project_dir / "game"
    game_dir.mkdir(parents=True)
    (game_dir / "custom_story.rpy").write_text("label start:\n    return\n", encoding="utf-8")

    res = ProjectValidator.validate(project_dir)
    assert res.is_valid
    assert len(res.errors) == 0
    # Must have warnings indicating missing common options.rpy and script.rpy
    assert any("options.rpy" in warn for warn in res.warnings)
    assert any("script.rpy" in warn for warn in res.warnings)


def test_validator_when_game_dir_selected_directly(tmp_path: Path):
    """If user selects the game/ directory directly, it should resolve root and game correctly."""
    project_dir = tmp_path / "selected_game_direct"
    game_dir = project_dir / "game"
    game_dir.mkdir(parents=True)
    (game_dir / "script.rpy").write_text("label start:\n    return\n", encoding="utf-8")

    res = ProjectValidator.validate(game_dir)
    assert res.is_valid
    assert res.root_path.resolve() == project_dir.resolve()
    assert res.game_path.resolve() == game_dir.resolve()


def test_validator_scripts_in_subfolders(tmp_path: Path):
    """Scripts located inside subfolders under game/ (e.g. game/story/main.rpy)
    should be detected."""
    project_dir = tmp_path / "subfolder_project"
    game_dir = project_dir / "game" / "story"
    game_dir.mkdir(parents=True)
    (game_dir / "main.rpy").write_text("label start:\n    return\n", encoding="utf-8")

    res = ProjectValidator.validate(project_dir)
    assert res.is_valid
    assert len(res.errors) == 0
