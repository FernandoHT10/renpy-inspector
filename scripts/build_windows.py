"""Automated Windows build script for compiling Ren'Py Inspector standalone executable."""

import shutil
import subprocess
import sys
from pathlib import Path


def build_executable() -> int:
    """Invokes PyInstaller using the renpy_inspector.spec file."""
    root_dir = Path(__file__).resolve().parent.parent
    spec_file = root_dir / "scripts" / "renpy_inspector.spec"
    if not spec_file.is_file():
        spec_file = root_dir / "renpy_inspector.spec"
    dist_dir = root_dir / "dist"
    build_dir = root_dir / "build"

    if not spec_file.is_file():
        print(f"Error: Specification file not found at '{spec_file}'")
        return 1

    print("Ren'Py Inspector — Windows Executable Builder")
    print("=============================================")
    print(f"Root Directory: {root_dir}")
    print(f"Spec File:      {spec_file.name}")
    print()

    # Clean previous build artifacts if requested or present
    for d in (build_dir, dist_dir):
        if d.is_dir():
            print(f"Cleaning previous {d.name}/ directory...")
            try:
                shutil.rmtree(d)
            except Exception as err:
                print(f"Warning: Could not remove {d}: {err}")

    # Run PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_file),
    ]

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=root_dir)

    if result.returncode != 0:
        print(f"Build failed with exit code {result.returncode}")
        return result.returncode

    exe_target = dist_dir / "RenPyInspector.exe"
    if not exe_target.exists():
        # Check folder mode
        exe_target = dist_dir / "RenPyInspector" / "RenPyInspector.exe"

    if exe_target.is_file():
        size_mb = exe_target.stat().st_size / (1024 * 1024)
        print()
        print("Build Succeeded!")
        print(f"Standalone executable: {exe_target}")
        print(f"Binary Size:           {size_mb:.2f} MB")
        return 0
    else:
        print("Error: Output executable was not found in dist/")
        return 1


if __name__ == "__main__":
    sys.exit(build_executable())
