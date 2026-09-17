"""Tests for AssetCatalog indexing, queries, and case-sensitivity infrastructure."""

from pathlib import Path

from renpy_inspector.core.models.asset import AssetInfo
from renpy_inspector.core.models.enums import AssetType
from renpy_inspector.core.scanner.asset_catalog import AssetCatalog


def test_catalog_indexing_and_normalization():
    """Paths must be normalized with POSIX forward slashes and indexed correctly."""
    asset1 = AssetInfo(
        relative_path=r"images\characters\hero.png",
        absolute_path=Path("/tmp/game/images/characters/hero.png"),
        asset_type=AssetType.IMAGE,
        filename="hero.png",
        extension=".png",
        size_bytes=500,
    )
    asset2 = AssetInfo(
        relative_path="audio/music/intro.ogg",
        absolute_path=Path("/tmp/game/audio/music/intro.ogg"),
        asset_type=AssetType.AUDIO,
        filename="intro.ogg",
        extension=".ogg",
        size_bytes=1500,
    )

    catalog = AssetCatalog([asset1, asset2])

    assert catalog.total_count() == 2
    assert "images/characters/hero.png" in catalog
    assert "audio/music/intro.ogg" in catalog

    hero = catalog.find_exact("images/characters/hero.png")
    assert hero is not None
    assert hero.size_bytes == 500
    assert hero.asset_type == AssetType.IMAGE

    music = catalog.get_by_type(AssetType.AUDIO)
    assert len(music) == 1
    assert music[0].filename == "intro.ogg"


def test_catalog_case_sensitivity_lookup():
    """Test case-insensitive queries and case-mismatch detection."""
    asset = AssetInfo(
        relative_path="images/sylvie_normal.png",
        absolute_path=Path("/tmp/game/images/sylvie_normal.png"),
        asset_type=AssetType.IMAGE,
        filename="sylvie_normal.png",
        extension=".png",
        size_bytes=3200,
    )

    catalog = AssetCatalog([asset])

    # 1. Exact match
    assert catalog.find_exact("images/sylvie_normal.png") is not None
    assert catalog.has_case_mismatch("images/sylvie_normal.png") is None

    # 2. Case-insensitive query
    matches = catalog.find_case_insensitive("images/SYLVIE_NORMAL.PNG")
    assert len(matches) == 1
    assert matches[0].relative_path == "images/sylvie_normal.png"

    # 3. Case mismatch detection
    mismatch = catalog.has_case_mismatch("images/Sylvie_Normal.png")
    assert mismatch == "images/sylvie_normal.png"

    mismatch_upper = catalog.has_case_mismatch("IMAGES/SYLVIE_NORMAL.PNG")
    assert mismatch_upper == "images/sylvie_normal.png"

    # 4. Non-existent file
    assert catalog.find_exact("images/nonexistent.png") is None
    assert catalog.find_case_insensitive("images/nonexistent.png") == []
    assert catalog.has_case_mismatch("images/nonexistent.png") is None
