"""Pytest fixtures for Ren'Py Inspector tests."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to the tests/fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def valid_minimal_project_dir(fixtures_dir: Path) -> Path:
    """Return path to the valid minimal fixture project."""
    return fixtures_dir / "valid_minimal_project"


@pytest.fixture
def temp_renpy_project(tmp_path: Path):
    """Factory fixture to create temporary custom Ren'Py projects on the fly."""

    def _create_project(
        files: dict[str, str] | None = None,
        create_game_dir: bool = True,
    ) -> Path:
        project_root = tmp_path / "custom_project"
        project_root.mkdir(parents=True, exist_ok=True)

        game_dir = project_root / "game"
        if create_game_dir:
            game_dir.mkdir(parents=True, exist_ok=True)

        if files:
            for rel_path, content in files.items():
                target = game_dir / rel_path if create_game_dir else project_root / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

        return project_root

    return _create_project
