"""Unit tests for Windows PyInstaller packaging configuration (Phase 9)."""

import ast
from pathlib import Path


def test_spec_file_syntax_and_structure():
    root_dir = Path(__file__).resolve().parent.parent
    spec_path = root_dir / "renpy_inspector.spec"

    assert spec_path.is_file(), "renpy_inspector.spec should exist"
    code = spec_path.read_text(encoding="utf-8")

    # Verify syntax validity via AST parse
    parsed_ast = ast.parse(code)
    assert isinstance(parsed_ast, ast.Module)

    # Check key configuration contents
    assert "PySide6" in code
    assert "renpy_inspector/gui/app.py" in code
    assert "RenPyInspector" in code
    assert "hiddenimports" in code
    assert "RPY-CODE-001" not in code  # spec contains module names, not rule IDs


def test_build_script_exists():
    root_dir = Path(__file__).resolve().parent.parent
    py_script = root_dir / "scripts" / "build_windows.py"
    ps_script = root_dir / "scripts" / "build_exe.ps1"

    assert py_script.is_file(), "build_windows.py must exist"
    assert ps_script.is_file(), "build_exe.ps1 must exist"

    # Verify build_windows.py parses
    ast.parse(py_script.read_text(encoding="utf-8"))
