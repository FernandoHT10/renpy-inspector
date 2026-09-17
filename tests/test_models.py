"""Tests for domain models, immutability, enums, and serialization."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from renpy_inspector.core.models.asset import AssetInfo
from renpy_inspector.core.models.enums import AssetType, Category, Confidence, Severity
from renpy_inspector.core.models.issue import Issue, generate_issue_id
from renpy_inspector.core.models.location import Location
from renpy_inspector.core.models.project import RenPyProject, ValidationResult
from renpy_inspector.core.models.symbols import (
    CallReference,
    ImageSymbol,
    JumpReference,
    LabelSymbol,
)


def test_enums_values():
    """Verify enum members and string representations."""
    assert Severity.CRITICAL == "CRITICAL"
    assert Severity.ERROR == "ERROR"
    assert Severity.WARNING == "WARNING"
    assert Severity.INFO == "INFO"

    assert Category.CODE == "Code"
    assert Category.ASSETS == "Assets"
    assert Category.AUDIO == "Audio"
    assert Category.IMAGES == "Images"
    assert Category.TRANSLATION == "Translation"
    assert Category.REFERENCES == "References"
    assert Category.STRUCTURE == "Project Structure"

    assert Confidence.CERTAIN == "CERTAIN"
    assert Confidence.SUSPECTED == "SUSPECTED"

    assert AssetType.SCRIPT == "script"
    assert AssetType.IMAGE == "image"
    assert AssetType.AUDIO == "audio"
    assert AssetType.FONT == "font"
    assert AssetType.UNKNOWN == "unknown"


def test_location_immutability_and_serialization():
    """Test Location model immutability, formatting, and dict conversion."""
    loc = Location(
        file_path="game/script.rpy",
        line_number=42,
        column_number=5,
        source_snippet="jump chapter_02",
    )

    with pytest.raises(FrozenInstanceError):
        loc.line_number = 100  # type: ignore

    assert str(loc) == "game/script.rpy:42:5"
    d = loc.to_dict()
    assert d == {
        "file_path": "game/script.rpy",
        "line_number": 42,
        "column_number": 5,
        "source_snippet": "jump chapter_02",
    }


def test_issue_creation_and_deterministic_id():
    """Test Issue factory, deterministic ID generation, and immutability."""
    loc = Location(file_path="game/script.rpy", line_number=184)
    msg = "The target label 'chapter_03' does not exist."

    id1 = generate_issue_id("RPY-CODE-001", "game/script.rpy", 184, msg)
    id2 = generate_issue_id("RPY-CODE-001", "game/script.rpy", 184, msg)
    assert id1 == id2
    assert len(id1) == 16

    issue = Issue.create(
        rule_id="RPY-CODE-001",
        severity=Severity.ERROR,
        category=Category.CODE,
        title="Broken jump",
        message=msg,
        location=loc,
        suggestion="Create the label or correct the jump target.",
    )

    assert issue.id == id1
    assert issue.severity == Severity.ERROR
    assert issue.confidence == Confidence.CERTAIN

    with pytest.raises(FrozenInstanceError):
        issue.title = "Modified"  # type: ignore

    d = issue.to_dict()
    assert d["id"] == id1
    assert d["rule_id"] == "RPY-CODE-001"
    assert d["severity"] == "ERROR"
    assert d["category"] == "Code"
    assert d["location"]["line_number"] == 184


def test_asset_info_model():
    """Test AssetInfo properties, serialization, and immutability."""
    asset = AssetInfo(
        relative_path="images/bg/room.png",
        absolute_path=Path("/tmp/game/images/bg/room.png"),
        asset_type=AssetType.IMAGE,
        filename="room.png",
        extension=".png",
        size_bytes=1024,
    )

    with pytest.raises(FrozenInstanceError):
        asset.size_bytes = 2048  # type: ignore

    d = asset.to_dict()
    assert d["relative_path"] == "images/bg/room.png"
    assert d["asset_type"] == "image"
    assert d["size_bytes"] == 1024


def test_validation_result_and_project_models():
    """Test ValidationResult and RenPyProject serialization and attributes."""
    res = ValidationResult(
        is_valid=True,
        root_path=Path("/game_root"),
        game_path=Path("/game_root/game"),
        detected_markers=("options.rpy", "script.rpy"),
        warnings=("Notice about font",),
        errors=(),
    )
    d = res.to_dict()
    assert d["is_valid"] is True
    assert d["detected_markers"] == ["options.rpy", "script.rpy"]
    assert d["warnings"] == ["Notice about font"]

    proj = RenPyProject(
        name="TestGame",
        root_path=Path("/game_root"),
        game_path=Path("/game_root/game"),
    )
    proj_d = proj.to_dict()
    assert proj_d["name"] == "TestGame"
    assert proj_d["is_valid"] is True


def test_symbol_models():
    """Test AST symbol placeholder models."""
    loc = Location(file_path="game/script.rpy", line_number=10)
    label = LabelSymbol(name=".choice", location=loc, is_local=True, parent_label="start")
    assert label.full_name == "start.choice"

    jump = JumpReference(target="start", location=loc)
    assert jump.target == "start"
    assert not jump.is_expression

    call = CallReference(target="expr", location=loc, is_expression=True)
    assert call.is_expression

    img = ImageSymbol(tag="eileen", attributes=("happy",), location=loc)
    assert img.full_tag == "eileen happy"
