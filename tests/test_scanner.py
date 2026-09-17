"""Tests for FileScanner and extension mapping."""

from pathlib import Path

from renpy_inspector.core.models.enums import AssetType
from renpy_inspector.core.scanner.file_scanner import FileScanner


def test_scanner_detects_all_supported_types(tmp_path: Path):
    """FileScanner must detect scripts, images, audio, and fonts accurately."""
    game_dir = tmp_path / "game"
    game_dir.mkdir()

    # Scripts
    (game_dir / "script.rpy").write_text("label start: pass", encoding="utf-8")
    (game_dir / "module.rpym").write_text("# module", encoding="utf-8")

    # Images
    images_dir = game_dir / "images"
    images_dir.mkdir()
    (images_dir / "img1.png").write_bytes(b"\x89PNG")
    (images_dir / "img2.jpg").write_bytes(b"\xff\xd8")
    (images_dir / "img3.jpeg").write_bytes(b"\xff\xd8")
    (images_dir / "img4.webp").write_bytes(b"RIFF")
    (images_dir / "img5.bmp").write_bytes(b"BM")
    (images_dir / "img6.gif").write_bytes(b"GIF89a")

    # Audio
    audio_dir = game_dir / "audio"
    audio_dir.mkdir()
    (audio_dir / "track.ogg").write_bytes(b"OggS")
    (audio_dir / "track.mp3").write_bytes(b"ID3")
    (audio_dir / "track.wav").write_bytes(b"RIFF")
    (audio_dir / "track.opus").write_bytes(b"OggS")

    # Fonts
    fonts_dir = game_dir / "fonts"
    fonts_dir.mkdir()
    (fonts_dir / "font1.ttf").write_bytes(b"\x00\x01\x00\x00")
    (fonts_dir / "font2.otf").write_bytes(b"OTTO")

    # Unknown extensions to be ignored
    (game_dir / "readme.txt").write_text("Hello", encoding="utf-8")
    (game_dir / "backup.bak").write_bytes(b"old")
    (game_dir / "data.json").write_text("{}", encoding="utf-8")

    scanner = FileScanner()
    catalog = scanner.scan(game_dir)

    counts = catalog.count_by_type()
    assert counts[AssetType.SCRIPT] == 2
    assert counts[AssetType.IMAGE] == 6
    assert counts[AssetType.AUDIO] == 4
    assert counts[AssetType.FONT] == 2
    assert catalog.total_count() == 14

    # Verify unknown files are NOT in catalog
    assert "readme.txt" not in catalog
    assert "backup.bak" not in catalog
    assert "data.json" not in catalog


def test_scanner_ignores_specified_directories(tmp_path: Path):
    """FileScanner must skip ignored directories like cache, .git, and __pycache__."""
    game_dir = tmp_path / "game"
    game_dir.mkdir()

    # Valid file
    (game_dir / "script.rpy").write_text("label start: pass", encoding="utf-8")

    # Files inside cache/ and .git/
    cache_dir = game_dir / "cache"
    cache_dir.mkdir()
    (cache_dir / "cached_image.png").write_bytes(b"PNG")

    git_dir = game_dir / ".git"
    git_dir.mkdir()
    (git_dir / "git_icon.png").write_bytes(b"PNG")

    scanner = FileScanner()
    catalog = scanner.scan(game_dir)

    assert catalog.total_count() == 1
    assert "script.rpy" in catalog
    assert "cache/cached_image.png" not in catalog
    assert ".git/git_icon.png" not in catalog


def test_scanner_progress_callback(valid_minimal_project_dir: Path):
    """FileScanner should invoke the progress callback for discovered assets."""
    discovered = []

    def callback(path: str):
        discovered.append(path)

    scanner = FileScanner(progress_callback=callback)
    catalog = scanner.scan(valid_minimal_project_dir / "game")

    assert len(discovered) == catalog.total_count()
    assert any("script.rpy" in p for p in discovered)


def test_scanner_deduplicates_rpym_when_rpy_present(tmp_path: Path):
    """FileScanner must skip .rpym files when a .rpy with identical stem exists in same folder."""
    game_dir = tmp_path / "game"
    game_dir.mkdir()

    (game_dir / "tutorial_director.rpy").write_text(
        "label director:\n    return\n", encoding="utf-8"
    )
    (game_dir / "tutorial_director.rpym").write_text(
        "label director:\n    return\n", encoding="utf-8"
    )
    (game_dir / "standalone_module.rpym").write_text(
        "label mod:\n    return\n", encoding="utf-8"
    )

    scanner = FileScanner()
    catalog = scanner.scan(game_dir)

    assert "tutorial_director.rpy" in catalog
    assert "tutorial_director.rpym" not in catalog
    assert "standalone_module.rpym" in catalog
